#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manage token-to-mailbox permissions for the email analysis MCP API."""

import argparse
import json
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_PERMISSIONS = ["read_index", "read_evidence"]


def load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"users": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_user(users: List[Dict[str, Any]], user_id: str) -> Optional[Dict[str, Any]]:
    for user in users:
        if str(user.get("user_id")) == user_id:
            return user
    return None


def cmd_list(args: argparse.Namespace) -> None:
    data = load(args.file)
    for user in data.get("users", []):
        print(json.dumps({
            "user_id": user.get("user_id"),
            "display_name": user.get("display_name"),
            "allowed_mailboxes": user.get("allowed_mailboxes", []),
            "permissions": user.get("permissions", []),
            "token_set": bool(user.get("token")),
        }, ensure_ascii=False))


def cmd_add_user(args: argparse.Namespace) -> None:
    data = load(args.file)
    users = data.setdefault("users", [])
    user = find_user(users, args.user_id)
    token = args.token or secrets.token_urlsafe(32)
    mailboxes = args.mailboxes or []
    permissions = args.permissions or DEFAULT_PERMISSIONS
    if args.allow_rebuild and "request_rebuild" not in permissions:
        permissions = permissions + ["request_rebuild"]
    if user:
        user.update({
            "display_name": args.display_name or user.get("display_name") or args.user_id,
            "token": token if args.rotate_token else user.get("token", token),
            "allowed_mailboxes": mailboxes,
            "permissions": permissions,
        })
    else:
        user = {
            "user_id": args.user_id,
            "display_name": args.display_name or args.user_id,
            "token": token,
            "allowed_mailboxes": mailboxes,
            "permissions": permissions,
        }
        users.append(user)
    save(args.file, data)
    print(json.dumps({
        "status": "ok",
        "user_id": user["user_id"],
        "token": user["token"],
        "allowed_mailboxes": user["allowed_mailboxes"],
        "permissions": user["permissions"],
    }, ensure_ascii=False, indent=2))


def cmd_remove_user(args: argparse.Namespace) -> None:
    data = load(args.file)
    before = len(data.get("users", []))
    data["users"] = [u for u in data.get("users", []) if str(u.get("user_id")) != args.user_id]
    save(args.file, data)
    print(json.dumps({"status": "ok", "removed": before - len(data["users"])}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True, help="permissions.json path")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add-user")
    p_add.add_argument("--user-id", required=True)
    p_add.add_argument("--display-name")
    p_add.add_argument("--mailboxes", nargs="*", default=[])
    p_add.add_argument("--permissions", nargs="*")
    p_add.add_argument("--token")
    p_add.add_argument("--rotate-token", action="store_true")
    p_add.add_argument("--allow-rebuild", action="store_true")
    p_add.set_defaults(func=cmd_add_user)

    p_rm = sub.add_parser("remove-user")
    p_rm.add_argument("--user-id", required=True)
    p_rm.set_defaults(func=cmd_remove_user)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.error("command is required")
    args.func(args)


if __name__ == "__main__":
    main()

