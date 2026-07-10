#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch operations for production mail indexing and permissions.

This script is intentionally conservative: it does not read raw mail content.
It discovers mailbox directories, builds per-mailbox changed-file lists from
file signatures, calls mail_indexer.py, and can create department/user tokens.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

INDEXABLE_SUFFIXES = {
    ".eml", ".ics", ".txt", ".html", ".htm", ".csv", ".json", ".docx",
}
DEFAULT_DEPARTMENTS = ["caigou", "yingxiao"]
DEFAULT_PERMISSIONS = ["read_index", "read_evidence"]


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError("%s is required" % name)
    return value


def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def now_text() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def safe_id(value: str) -> str:
    return value.replace("/", "__").replace("\\", "__")


def mailbox_root(raw_root: Path, mailbox_id: str) -> Path:
    path = (raw_root / mailbox_id).resolve()
    raw = raw_root.resolve()
    if raw != path and raw not in path.parents:
        raise ValueError("mailbox escapes MAIL_RAW_ROOT: %s" % mailbox_id)
    return path


def looks_like_mailbox(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "inbox").is_dir() or (path / "send").is_dir():
        return True
    try:
        for child in path.iterdir():
            if child.is_file() and child.suffix.lower() in INDEXABLE_SUFFIXES:
                return True
            if child.is_dir() and child.name in {"inbox", "send", "sent"}:
                return True
    except OSError:
        return False
    return False


def discover_mailboxes(raw_root: Path, departments: Iterable[str]) -> List[str]:
    found: List[str] = []
    for dept in departments:
        dept_dir = raw_root / dept
        if not dept_dir.is_dir():
            continue
        for account in sorted(p for p in dept_dir.iterdir() if p.is_dir()):
            if looks_like_mailbox(account):
                found.append("%s/%s" % (dept, account.name))
    return found


def iter_candidate_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        suffix = path.suffix.lower()
        if suffix in INDEXABLE_SUFFIXES:
            yield path


def file_signature(path: Path) -> Dict[str, Any]:
    st = path.stat()
    return {"size": int(st.st_size), "mtime_ns": int(st.st_mtime_ns)}


def manifest_path(index_root: Path, mailbox_id: str) -> Path:
    return index_root / mailbox_id / "state" / "file_manifest.json"


def load_manifest(index_root: Path, mailbox_id: str) -> Dict[str, Dict[str, Any]]:
    path = manifest_path(index_root, mailbox_id)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return dict(payload.get("files", {}))
    except Exception:
        return {}


def save_manifest(index_root: Path, mailbox_id: str, files: Dict[str, Dict[str, Any]]) -> None:
    path = manifest_path(index_root, mailbox_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"mailbox_id": mailbox_id, "generated_at": now_text(), "files": files}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_changed_list(log_root: Path, mailbox_id: str, rels: List[str]) -> Path:
    out_dir = log_root / "changed_lists"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ("%s_%s.txt" % (safe_id(mailbox_id), now_stamp()))
    path.write_text("\n".join(rels) + ("\n" if rels else ""), encoding="utf-8")
    return path


def build_changed_list(raw_root: Path, index_root: Path, log_root: Path, mailbox_id: str) -> Tuple[Path, Dict[str, Any], Dict[str, Dict[str, Any]]]:
    root = mailbox_root(raw_root, mailbox_id)
    previous = load_manifest(index_root, mailbox_id)
    current: Dict[str, Dict[str, Any]] = {}
    changed: List[str] = []

    for path in iter_candidate_files(root):
        rel = path.relative_to(root).as_posix()
        sig = file_signature(path)
        current[rel] = sig
        if previous.get(rel) != sig:
            changed.append(rel)

    for rel in sorted(set(previous) - set(current)):
        changed.append(rel)

    changed = sorted(dict.fromkeys(changed))
    changed_path = write_changed_list(log_root, mailbox_id, changed)
    summary = {
        "mailbox_id": mailbox_id,
        "changed_list": str(changed_path),
        "current_file_count": len(current),
        "previous_file_count": len(previous),
        "changed_file_count": len(changed),
    }
    return changed_path, summary, current


def run_indexer(server_app_root: Path, mailbox_id: str, changed_list: Optional[Path], mode: str, max_groups: Optional[int]) -> int:
    cmd = [sys.executable, str(server_app_root / "mail_indexer.py")]
    if changed_list is not None:
        cmd.extend(["--changed-list", str(changed_list), "--job-type", "incremental"])
    else:
        cmd.extend(["--job-type", "backfill"])
    if max_groups:
        cmd.extend(["--max-groups", str(max_groups)])
    cmd.append(mailbox_id)
    print("[%s] %s" % (now_text(), " ".join(cmd)), flush=True)
    return subprocess.call(cmd, cwd=str(server_app_root))


def cmd_discover(args: argparse.Namespace) -> None:
    raw_root = Path(required_env("MAIL_RAW_ROOT"))
    departments = args.departments or DEFAULT_DEPARTMENTS
    mailboxes = discover_mailboxes(raw_root, departments)
    payload = {"generated_at": now_text(), "raw_root": str(raw_root), "departments": departments, "mailboxes": mailboxes}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def selected_mailboxes(args: argparse.Namespace) -> List[str]:
    raw_root = Path(required_env("MAIL_RAW_ROOT"))
    if args.mailbox:
        return list(args.mailbox)
    if args.mailbox_list:
        return [line.strip() for line in args.mailbox_list.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
    return discover_mailboxes(raw_root, args.departments or DEFAULT_DEPARTMENTS)


def cmd_index(args: argparse.Namespace) -> None:
    raw_root = Path(required_env("MAIL_RAW_ROOT"))
    index_root = Path(required_env("MAIL_INDEX_ROOT"))
    log_root = Path(required_env("MAIL_LOG_ROOT"))
    server_app_root = Path(os.environ.get("SERVER_APP_ROOT", Path(__file__).resolve().parent))
    mailboxes = selected_mailboxes(args)
    results: List[Dict[str, Any]] = []
    for mailbox_id in mailboxes:
        current_manifest: Optional[Dict[str, Dict[str, Any]]] = None
        changed_path: Optional[Path] = None
        summary: Dict[str, Any] = {"mailbox_id": mailbox_id}
        if args.mode == "incremental":
            changed_path, summary, current_manifest = build_changed_list(raw_root, index_root, log_root, mailbox_id)
            if summary["changed_file_count"] == 0 and not args.force:
                summary["status"] = "skipped_no_changes"
                results.append(summary)
                print(json.dumps(summary, ensure_ascii=False), flush=True)
                continue
        elif args.mode == "backfill":
            changed_path = None
        else:
            raise RuntimeError("unknown mode: %s" % args.mode)

        if args.dry_run:
            summary["status"] = "dry_run"
            results.append(summary)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            continue

        code = run_indexer(server_app_root, mailbox_id, changed_path, args.mode, args.max_groups)
        summary["exit_code"] = code
        summary["status"] = "ok" if code == 0 else "failed"
        if code == 0 and current_manifest is not None and not args.max_groups:
            save_manifest(index_root, mailbox_id, current_manifest)
        results.append(summary)
    batch = {"generated_at": now_text(), "mode": args.mode, "mailbox_count": len(mailboxes), "results": results}
    out = log_root / ("batch_index_%s.json" % now_stamp())
    out.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"batch_status": str(out), "results": results}, ensure_ascii=False, indent=2))


def load_permissions(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"users": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_permissions(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def upsert_user(payload: Dict[str, Any], user_id: str, display_name: str, mailboxes: List[str], permissions: List[str], rotate: bool) -> Dict[str, Any]:
    import secrets
    users = payload.setdefault("users", [])
    user = None
    for item in users:
        if item.get("user_id") == user_id:
            user = item
            break
    if user is None:
        user = {"user_id": user_id, "token": secrets.token_urlsafe(32)}
        users.append(user)
    elif rotate or not user.get("token"):
        user["token"] = secrets.token_urlsafe(32)
    user["display_name"] = display_name
    user["allowed_mailboxes"] = mailboxes
    user["permissions"] = permissions
    return user


def cmd_grant_departments(args: argparse.Namespace) -> None:
    permissions_file = Path(required_env("MAIL_PERMISSIONS_FILE"))
    raw_root = Path(required_env("MAIL_RAW_ROOT"))
    payload = load_permissions(permissions_file)
    departments = args.departments or DEFAULT_DEPARTMENTS
    created: List[Dict[str, Any]] = []
    all_mailboxes: List[str] = []
    for dept in departments:
        dept_mailboxes = discover_mailboxes(raw_root, [dept])
        all_mailboxes.extend(dept_mailboxes)
        if args.create_department_users:
            user = upsert_user(
                payload,
                "%s_all" % dept,
                "%s 全部邮箱" % dept,
                dept_mailboxes,
                DEFAULT_PERMISSIONS,
                args.rotate_token,
            )
            created.append(user)
    if args.admin_user_id:
        user = upsert_user(
            payload,
            args.admin_user_id,
            args.admin_display_name or "邮件问数管理员",
            sorted(dict.fromkeys(all_mailboxes)),
            DEFAULT_PERMISSIONS + (["request_rebuild"] if args.allow_rebuild else []),
            args.rotate_token,
        )
        created.append(user)
    if not args.dry_run:
        save_permissions(permissions_file, payload)
    print(json.dumps({"permissions_file": str(permissions_file), "dry_run": args.dry_run, "users": created}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    p_discover = sub.add_parser("discover")
    p_discover.add_argument("--departments", nargs="*")
    p_discover.add_argument("--output", type=Path)
    p_discover.set_defaults(func=cmd_discover)

    p_index = sub.add_parser("index")
    p_index.add_argument("--mode", choices=["incremental", "backfill"], default="incremental")
    p_index.add_argument("--departments", nargs="*")
    p_index.add_argument("--mailbox", action="append")
    p_index.add_argument("--mailbox-list", type=Path)
    p_index.add_argument("--max-groups", type=int)
    p_index.add_argument("--force", action="store_true", help="Run indexer even when incremental changed list is empty.")
    p_index.add_argument("--dry-run", action="store_true")
    p_index.set_defaults(func=cmd_index)

    p_grant = sub.add_parser("grant-departments")
    p_grant.add_argument("--departments", nargs="*")
    p_grant.add_argument("--create-department-users", action="store_true")
    p_grant.add_argument("--admin-user-id")
    p_grant.add_argument("--admin-display-name")
    p_grant.add_argument("--allow-rebuild", action="store_true")
    p_grant.add_argument("--rotate-token", action="store_true")
    p_grant.add_argument("--dry-run", action="store_true")
    p_grant.set_defaults(func=cmd_grant_departments)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.error("command is required")
    args.func(args)


if __name__ == "__main__":
    main()

