#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server-side lightweight mail indexer v3.

Builds mailbox-scoped indexes on the server. It groups files by exported message
folder, skips empty attachment placeholders, extracts useful subjects from folder
names / EML headers / ICS SUMMARY / Word mail exports, and writes JSON indexes under
$MAIL_INDEX_ROOT/<mailbox_id>.
"""

from __future__ import annotations

import argparse
import email
import email.policy
import email.utils
import hashlib
import html
import json
import os
import sqlite3
import uuid
import re
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value

RAW_ROOT = Path(required_env("MAIL_RAW_ROOT")).resolve()
INDEX_ROOT = Path(required_env("MAIL_INDEX_ROOT")).resolve()
LOG_ROOT = Path(required_env("MAIL_LOG_ROOT")).resolve()
MAX_READ_BYTES = int(os.environ.get("MAIL_INDEX_MAX_READ_BYTES", str(512 * 1024)))
MAX_EVIDENCE = int(os.environ.get("MAIL_INDEX_MAX_EVIDENCE", "80000"))
MAX_EXCERPT_CHARS = int(os.environ.get("MAIL_INDEX_MAX_EXCERPT_CHARS", "4000"))

DEFAULT_BUSINESS_KEYWORDS = [
    "付款", "审批", "合同", "报价", "订单", "发票", "交付", "延期", "风险", "问题", "客户", "项目",
    "合作", "尽调", "due diligence", "information request", "样品", "测试", "质量", "生产", "物料",
    "供应商", "会议", "回复", "确认", "变更", "报表", "利润", "应收", "应付", "索赔", "审计",
    "documentation", "invoice", "payment", "approval", "meeting", "claim", "report", "margin",
]
EXTRA_BUSINESS_KEYWORDS = [
    item.strip()
    for item in os.environ.get("MAIL_INDEX_EXTRA_KEYWORDS", "").split(",")
    if item.strip()
]
BUSINESS_KEYWORDS = list(dict.fromkeys(DEFAULT_BUSINESS_KEYWORDS + EXTRA_BUSINESS_KEYWORDS))

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pdf", ".zip", ".rar", ".7z", ".gz",
    ".xlsx", ".xls", ".doc", ".pptx", ".ppt", ".exe", ".bin", ".db", ".sqlite",
}
TEXT_SUFFIXES = {".txt", ".html", ".htm", ".eml", ".ics", ".csv", ".json", ""}
DOCX_SUFFIXES = {".docx"}
ATTACHMENT_SUFFIXES = BINARY_SUFFIXES | DOCX_SUFFIXES
ARCHIVE_SUFFIXES = {".zip", ".rar", ".7z", ".gz"}

HEADER_PATTERNS = {
    "subject": [r"^Subject:\s*(.+)$", r"^主题[:：]\s*(.+)$", r"^标题[:：]\s*(.+)$", r"^邮件主题[:：]\s*(.+)$"],
    "sender": [r"^From:\s*(.+)$", r"^发件人[:：]\s*(.+)$", r"^发送人[:：]\s*(.+)$", r"^寄件人[:：]\s*(.+)$"],
    "recipients": [r"^To:\s*(.+)$", r"^收件人[:：]\s*(.+)$", r"^接收人[:：]\s*(.+)$"],
    "cc": [r"^Cc:\s*(.+)$", r"^抄送[:：]\s*(.+)$", r"^CC[:：]\s*(.+)$"],
    "sent_at": [r"^Date:\s*(.+)$", r"^时间[:：]\s*(.+)$", r"^发送时间[:：]\s*(.+)$", r"^日期[:：]\s*(.+)$"],
}


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def stable_id(prefix: str, value: str) -> str:
    return prefix + hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def safe_child(root: Path, child: str) -> Path:
    path = (root / child).resolve()
    if root != path and root not in path.parents:
        raise ValueError("path escapes root")
    return path


def read_sample(path: Path) -> str:
    with path.open("rb") as f:
        data = f.read(MAX_READ_BYTES)
    if b"\x00" in data[:4096]:
        return ""
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return data.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def clean_text(text: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p>|</div>|</li>|</tr>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()



def read_docx_text(path: Path) -> str:
    """Extract plain text from a .docx file without external dependencies."""
    xml_names = [
        "word/document.xml",
        "word/header1.xml",
        "word/header2.xml",
        "word/header3.xml",
        "word/footer1.xml",
        "word/footer2.xml",
        "word/footer3.xml",
    ]
    parts: List[str] = []
    try:
        with zipfile.ZipFile(path) as docx:
            names = set(docx.namelist())
            for name in xml_names:
                if name not in names:
                    continue
                root = ElementTree.fromstring(docx.read(name))
                for elem in root.iter():
                    tag = elem.tag.rsplit("}", 1)[-1]
                    if tag == "t" and elem.text:
                        parts.append(elem.text)
                    elif tag in {"br", "cr"}:
                        parts.append("\n")
                    elif tag == "tab":
                        parts.append("\t")
                    elif tag == "p":
                        parts.append("\n")
    except Exception:
        return ""
    return clean_text("".join(parts))


def looks_like_mail_docx(text: str, path: Path) -> bool:
    lower_name = path.name.lower()
    if "邮件提取" in path.name or "mail" in lower_name or "email" in lower_name:
        return bool(text.strip())
    header_hits = 0
    for key in ("subject", "sender", "recipients", "sent_at"):
        if regex_header(text, key):
            header_hits += 1
    if header_hits >= 2:
        return True
    lowered = text.lower()
    return ("from:" in lowered and "to:" in lowered) or ("发件人" in text and "收件人" in text)
def is_empty_placeholder(text: str, path: Path) -> bool:
    plain = clean_text(text)
    if path.name.lower().startswith("att") and len(plain) < 30:
        return True
    if "aria-label=\"Message Body\"" in text and len(plain) < 30:
        return True
    return False


def unfold_ics(text: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", text)


def ics_field(text: str, key: str) -> str:
    unfolded = unfold_ics(text)
    match = re.search(rf"^{re.escape(key)}(?:;[^:]*)?:(.*)$", unfolded, flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).replace("\\,", ",").replace("\\n", "\n").strip()


def decode_eml(raw: str) -> Dict[str, Any]:
    try:
        msg = email.message_from_string(raw, policy=email.policy.default)
    except Exception:
        return {}
    result: Dict[str, Any] = {
        "subject": str(msg.get("subject") or ""),
        "sender": str(msg.get("from") or ""),
        "recipients": str(msg.get("to") or ""),
        "cc": str(msg.get("cc") or ""),
        "sent_at": str(msg.get("date") or ""),
    }
    attachments: List[str] = []
    bodies: List[str] = []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        filename = part.get_filename()
        if filename:
            attachments.append(filename)
            continue
        if part.get_content_type() in {"text/plain", "text/html"}:
            try:
                bodies.append(str(part.get_content()))
            except Exception:
                pass
    result["attachments"] = attachments
    result["body"] = clean_text("\n".join(bodies))
    return result


def regex_header(raw: str, key: str) -> str:
    for pattern in HEADER_PATTERNS.get(key, []):
        match = re.search(pattern, raw, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def subject_from_folder(name: str) -> str:
    s = name.strip()
    s = re.sub(r"^\d{4}[-_]\d{2}[-_]\d{2}\s+\d{3,4}\s*", "", s)
    s = re.sub(r"^\d{4}[-_]\d{2}[-_]\d{2}\s*", "", s)
    s = re.sub(r"(?i)^(re|fw|fwd)[-：:\s]+", "", s).strip()
    s = s.replace("- ", " ").replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    return s[:220] or name[:220]



def subject_from_docx_filename(name: str) -> str:
    s = re.sub(r"\.docx$", "", name, flags=re.IGNORECASE)
    s = re.sub(r"_?邮件提取$", "", s)
    return subject_from_folder(s)
def message_key(raw_root: Path, path: Path) -> Tuple[str, Path]:
    rel_parts = path.relative_to(raw_root).parts
    if "attachments" in rel_parts:
        idx = rel_parts.index("attachments")
        if idx > 0:
            folder = raw_root.joinpath(*rel_parts[:idx])
            return folder.relative_to(raw_root).as_posix(), folder
    if len(rel_parts) >= 2:
        folder = raw_root.joinpath(*rel_parts[:-1])
        return folder.relative_to(raw_root).as_posix(), folder
    return path.relative_to(raw_root).as_posix(), path


def iter_files(mailbox_root: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(mailbox_root):
        dirs.sort()
        files.sort()
        for name in files:
            yield Path(root) / name


def collect_groups(mailbox_root: Path) -> Tuple[Dict[str, Dict[str, Any]], int]:
    groups: Dict[str, Dict[str, Any]] = {}
    skipped = 0
    for path in iter_files(mailbox_root):
        key, folder = message_key(mailbox_root, path)
        group = groups.setdefault(key, {"folder": folder, "files": [], "attachments": [], "archives": [], "texts": [], "metas": []})
        rel = path.relative_to(mailbox_root).as_posix()
        suffix = path.suffix.lower()
        if suffix == ".docx":
            text = read_docx_text(path)
            if looks_like_mail_docx(text, path):
                meta = {
                    "relative_path": rel,
                    "raw_path": str(path),
                    "file_mtime": path.stat().st_mtime,
                    "subject": regex_header(text, "subject") or subject_from_docx_filename(path.name),
                    "sender": regex_header(text, "sender"),
                    "recipients": regex_header(text, "recipients"),
                    "cc": regex_header(text, "cc"),
                    "sent_at": regex_header(text, "sent_at"),
                    "body": text,
                    "source_type": "docx_mail_export",
                }
                group["files"].append(rel)
                group["texts"].append(meta.get("body", ""))
                group["metas"].append(meta)
            else:
                group["attachments"].append(path.name)
                skipped += 1
            continue
        if "attachments" in path.parts or suffix in ATTACHMENT_SUFFIXES:
            group["attachments"].append(path.name)
        if suffix in ARCHIVE_SUFFIXES:
            group["archives"].append(path.name)
        if suffix in BINARY_SUFFIXES or suffix not in TEXT_SUFFIXES:
            skipped += 1
            continue
        try:
            text = read_sample(path)
        except Exception:
            skipped += 1
            continue
        if not text.strip() or is_empty_placeholder(text, path):
            skipped += 1
            continue
        meta: Dict[str, Any] = {"relative_path": rel, "raw_path": str(path), "file_mtime": path.stat().st_mtime}
        if path.suffix.lower() == ".ics" or "BEGIN:VCALENDAR" in text[:1000]:
            meta.update({
                "subject": ics_field(text, "SUMMARY"),
                "sender": ics_field(text, "ORGANIZER"),
                "recipients": "; ".join(re.findall(r"ATTENDEE[^:]*:mailto:([^\r\n]+)", unfold_ics(text), flags=re.IGNORECASE)),
                "sent_at": ics_field(text, "DTSTART") or ics_field(text, "DTSTAMP"),
                "body": clean_text(ics_field(text, "DESCRIPTION") or text),
            })
        else:
            parsed = decode_eml(text) if ("Subject:" in text[:5000] or "From:" in text[:5000]) else {}
            meta.update({
                "subject": parsed.get("subject") or regex_header(text, "subject") or "",
                "sender": parsed.get("sender") or regex_header(text, "sender") or "",
                "recipients": parsed.get("recipients") or regex_header(text, "recipients") or "",
                "cc": parsed.get("cc") or regex_header(text, "cc") or "",
                "sent_at": parsed.get("sent_at") or regex_header(text, "sent_at") or "",
                "body": parsed.get("body") or clean_text(text),
            })
        group["files"].append(rel)
        group["texts"].append(meta.get("body", ""))
        group["metas"].append(meta)
    return groups, skipped


def group_to_record(mailbox_id: str, raw_root: Path, key: str, group: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    metas = group.get("metas", [])
    if not metas:
        return None
    folder = group["folder"]
    folder_subject = subject_from_folder(folder.name if folder.is_dir() else Path(key).stem)
    best = next((m for m in metas if m.get("subject") and not re.match(r"(?i)^ATT\d+", m.get("subject", ""))), metas[0])
    subject = best.get("subject") or folder_subject
    if re.match(r"(?i)^ATT\d+", subject) or subject.startswith("未命名的附件"):
        subject = folder_subject
    body = clean_text("\n".join(t for t in group.get("texts", []) if t))
    if len(body) < 10 and not group.get("attachments"):
        return None
    mtime = max((m.get("file_mtime", 0) for m in metas), default=folder.stat().st_mtime if folder.exists() else time.time())
    sent_at = best.get("sent_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
    evidence_id = stable_id("ev_", mailbox_id + "/" + key)
    thread_key = re.sub(r"(?i)^(re|fw|fwd)\s*[:：-]\s*", "", subject).strip() or folder_subject
    thread_id = stable_id("th_", mailbox_id + "/" + thread_key)
    lowered = (subject + "\n" + body + "\n" + "\n".join(group.get("attachments", []))).lower()
    keywords = [kw for kw in BUSINESS_KEYWORDS if kw.lower() in lowered]
    return {
        "evidence_id": evidence_id,
        "message_id": stable_id("msg_", mailbox_id + "/" + key),
        "thread_id": thread_id,
        "mailbox_id": mailbox_id,
        "subject": subject[:220],
        "sender": best.get("sender", ""),
        "recipients": best.get("recipients", ""),
        "cc": best.get("cc", ""),
        "sent_at": sent_at,
        "file_mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
        "relative_path": key,
        "raw_path": str(folder),
        "source_files": group.get("files", [])[:50],
        "attachments": sorted(set(group.get("attachments", [])))[:50],
        "keywords": keywords,
        "excerpt": body[:MAX_EXCERPT_CHARS],
    }


def split_people(value: str) -> Iterable[str]:
    for part in re.split(r"[,;；、]\s*", value or ""):
        part = part.strip()
        if part:
            yield part[:120]


PARSER_VERSION = os.environ.get("MAIL_INDEX_PARSER_VERSION", "v4-production-sharded")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def rel_path(root: Path, rel: str) -> Path:
    return root.joinpath(*[p for p in rel.replace("\\", "/").split("/") if p and p != "."])


def normalize_changed(mailbox_root: Path, line: str) -> str:
    raw = line.strip().replace("\\", "/")
    if not raw or raw.startswith("#"):
        return ""
    p = Path(raw)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(mailbox_root).as_posix()
        except ValueError:
            return raw.lstrip("/")
    return re.sub(r"^(\./)+", "", raw).lstrip("/")


def load_changed_paths(mailbox_root: Path, changed_list: Optional[Path]) -> List[str]:
    if changed_list is None:
        return [p.relative_to(mailbox_root).as_posix() for p in iter_files(mailbox_root)]
    return [p for p in (normalize_changed(mailbox_root, line) for line in changed_list.read_text(encoding="utf-8").splitlines()) if p]


def file_sig(path: Path) -> Tuple[int, int]:
    st = path.stat()
    return st.st_size, getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))


def connect_state(index_dir: Path) -> sqlite3.Connection:
    state_dir = index_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(state_dir / "indexed_files.sqlite")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        create table if not exists indexed_files (
            mailbox_id text not null,
            relative_path text not null,
            file_size integer,
            mtime_ns integer,
            content_hash text,
            parser_version text,
            message_key text,
            record_id text,
            thread_id text,
            evidence_id text,
            shard_id text,
            status text not null,
            error_message text,
            retry_count integer not null default 0,
            first_seen_at text,
            last_seen_at text,
            indexed_at text,
            run_id text,
            primary key (mailbox_id, relative_path)
        );
        create table if not exists evidence_records (
            mailbox_id text not null,
            evidence_id text primary key,
            message_key text not null,
            thread_id text not null,
            shard_id text not null,
            record_json text not null,
            updated_at text not null,
            run_id text not null
        );
        create table if not exists index_jobs (
            job_id text primary key,
            mailbox_id text not null,
            job_type text not null,
            shard_id text,
            status text not null,
            cursor text,
            lease_owner text,
            lease_expires_at text,
            started_at text,
            finished_at text,
            error_message text
        );
        create index if not exists idx_indexed_files_status on indexed_files(mailbox_id, status);
        create index if not exists idx_indexed_files_message on indexed_files(mailbox_id, message_key);
        create index if not exists idx_evidence_records_shard on evidence_records(mailbox_id, shard_id);
        create index if not exists idx_evidence_records_thread on evidence_records(mailbox_id, thread_id);
        """
    )
    conn.commit()
    return conn


def state_row(conn: sqlite3.Connection, mailbox_id: str, relative_path: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "select * from indexed_files where mailbox_id = ? and relative_path = ?",
        (mailbox_id, relative_path),
    ).fetchone()


def upsert_state(
    conn: sqlite3.Connection,
    mailbox_id: str,
    relative_path: str,
    status: str,
    run_id: str,
    *,
    file_size: Optional[int] = None,
    mtime_ns: Optional[int] = None,
    message_key_value: str = "",
    record_id: str = "",
    thread_id: str = "",
    evidence_id: str = "",
    shard_id: str = "",
    error_message: str = "",
) -> None:
    old = state_row(conn, mailbox_id, relative_path)
    first_seen = old["first_seen_at"] if old and old["first_seen_at"] else now()
    retry_count = (int(old["retry_count"] or 0) + 1) if old and status == "failed" else 0
    conn.execute(
        """
        insert into indexed_files (
            mailbox_id, relative_path, file_size, mtime_ns, content_hash, parser_version,
            message_key, record_id, thread_id, evidence_id, shard_id, status, error_message,
            retry_count, first_seen_at, last_seen_at, indexed_at, run_id
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(mailbox_id, relative_path) do update set
            file_size = excluded.file_size,
            mtime_ns = excluded.mtime_ns,
            content_hash = excluded.content_hash,
            parser_version = excluded.parser_version,
            message_key = excluded.message_key,
            record_id = excluded.record_id,
            thread_id = excluded.thread_id,
            evidence_id = excluded.evidence_id,
            shard_id = excluded.shard_id,
            status = excluded.status,
            error_message = excluded.error_message,
            retry_count = excluded.retry_count,
            first_seen_at = coalesce(indexed_files.first_seen_at, excluded.first_seen_at),
            last_seen_at = excluded.last_seen_at,
            indexed_at = excluded.indexed_at,
            run_id = excluded.run_id
        """,
        (
            mailbox_id, relative_path, file_size, mtime_ns, "", PARSER_VERSION,
            message_key_value, record_id, thread_id, evidence_id, shard_id, status,
            error_message, retry_count, first_seen, now(), now(), run_id,
        ),
    )


def new_group_v4(folder: Path) -> Dict[str, Any]:
    return {"folder": folder, "all_files": [], "files": [], "attachments": [], "archives": [], "texts": [], "metas": []}


def add_file_v4(mailbox_root: Path, path: Path, groups: Dict[str, Dict[str, Any]]) -> int:
    key, folder = message_key(mailbox_root, path)
    group = groups.setdefault(key, new_group_v4(folder))
    rel = path.relative_to(mailbox_root).as_posix()
    group["all_files"].append(rel)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        text = read_docx_text(path)
        if looks_like_mail_docx(text, path):
            meta = {"relative_path": rel, "raw_path": str(path), "file_mtime": path.stat().st_mtime, "subject": regex_header(text, "subject") or subject_from_docx_filename(path.name), "sender": regex_header(text, "sender"), "recipients": regex_header(text, "recipients"), "cc": regex_header(text, "cc"), "sent_at": regex_header(text, "sent_at"), "body": text, "source_type": "docx_mail_export"}
            group["files"].append(rel); group["texts"].append(meta.get("body", "")); group["metas"].append(meta)
            return 0
        group["attachments"].append(path.name)
        return 1
    if "attachments" in path.relative_to(mailbox_root).parts or suffix in ATTACHMENT_SUFFIXES:
        group["attachments"].append(path.name)
    if suffix in ARCHIVE_SUFFIXES:
        group["archives"].append(path.name)
    if suffix in BINARY_SUFFIXES or suffix not in TEXT_SUFFIXES:
        return 1
    try:
        text = read_sample(path)
    except Exception:
        return 1
    if not text.strip() or is_empty_placeholder(text, path):
        return 1
    meta: Dict[str, Any] = {"relative_path": rel, "raw_path": str(path), "file_mtime": path.stat().st_mtime}
    if path.suffix.lower() == ".ics" or "BEGIN:VCALENDAR" in text[:1000]:
        meta.update({"subject": ics_field(text, "SUMMARY"), "sender": ics_field(text, "ORGANIZER"), "recipients": "; ".join(re.findall(r"ATTENDEE[^:]*:mailto:([^\r\n]+)", unfold_ics(text), flags=re.IGNORECASE)), "sent_at": ics_field(text, "DTSTART") or ics_field(text, "DTSTAMP"), "body": clean_text(ics_field(text, "DESCRIPTION") or text), "source_type": "ics"})
    else:
        parsed = decode_eml(text) if ("Subject:" in text[:5000] or "From:" in text[:5000]) else {}
        group["attachments"].extend(parsed.get("attachments", []))
        meta.update({"subject": parsed.get("subject") or regex_header(text, "subject") or "", "sender": parsed.get("sender") or regex_header(text, "sender") or "", "recipients": parsed.get("recipients") or regex_header(text, "recipients") or "", "cc": parsed.get("cc") or regex_header(text, "cc") or "", "sent_at": parsed.get("sent_at") or regex_header(text, "sent_at") or "", "body": parsed.get("body") or clean_text(text), "source_type": "eml_or_text"})
    group["files"].append(rel); group["texts"].append(meta.get("body", "")); group["metas"].append(meta)
    return 0


def collect_group_v4(mailbox_root: Path, key: str) -> Tuple[Dict[str, Any], int]:
    folder = rel_path(mailbox_root, key)
    groups: Dict[str, Dict[str, Any]] = {}
    skipped = 0
    if folder.is_dir():
        for path in iter_files(folder):
            skipped += add_file_v4(mailbox_root, path, groups)
    elif folder.is_file():
        skipped += add_file_v4(mailbox_root, folder, groups)
    return groups.get(key, new_group_v4(folder)), skipped


def shard_id_for_record(record: Dict[str, Any]) -> str:
    for value in (record.get("sent_at"), record.get("file_mtime")):
        if not value:
            continue
        try:
            dt = email.utils.parsedate_to_datetime(str(value))
            if dt:
                return f"{dt.year:04d}/{dt.month:02d}"
        except Exception:
            pass
        m = re.search(r"(19\d{2}|20\d{2})[-/年. ]{0,2}(\d{1,2})", str(value))
        if m:
            return f"{int(m.group(1)):04d}/{int(m.group(2)):02d}"
    return "unknown"


def public_record(record: Dict[str, Any], shard_id: str) -> Dict[str, Any]:
    item = dict(record)
    item.pop("raw_path", None)
    item["shard_id"] = shard_id
    item["indexer_version"] = PARSER_VERSION
    return item


def delete_records_for_message(conn: sqlite3.Connection, mailbox_id: str, message_key_value: str) -> Set[str]:
    rows = conn.execute("select shard_id from evidence_records where mailbox_id = ? and message_key = ?", (mailbox_id, message_key_value)).fetchall()
    conn.execute("delete from evidence_records where mailbox_id = ? and message_key = ?", (mailbox_id, message_key_value))
    return {row["shard_id"] for row in rows if row["shard_id"]}


def build_thread_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["thread_id"]].append(record)
    threads = []
    for thread_id, items in grouped.items():
        items.sort(key=lambda x: x.get("sent_at") or x.get("file_mtime") or "")
        participants = Counter()
        for item in items:
            for field in ("sender", "recipients", "cc"):
                participants.update(split_people(item.get(field, "")))
        threads.append({"thread_id": thread_id, "subject": items[0].get("subject") or "", "status": "indexed", "participants": [name for name, _ in participants.most_common(20)], "started_at": items[0].get("sent_at") or items[0].get("file_mtime"), "last_updated_at": items[-1].get("sent_at") or items[-1].get("file_mtime"), "message_count": len(items), "evidence_ids": [item["evidence_id"] for item in items[:100]], "summary": (items[-1].get("excerpt") or "")[:800], "shard_ids": sorted(set(item.get("shard_id", "unknown") for item in items))})
    threads.sort(key=lambda x: x.get("last_updated_at") or "", reverse=True)
    return threads


def load_records(conn: sqlite3.Connection, mailbox_id: str, shard_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if shard_id:
        rows = conn.execute("select record_json from evidence_records where mailbox_id = ? and shard_id = ? order by evidence_id", (mailbox_id, shard_id)).fetchall()
    else:
        rows = conn.execute("select record_json from evidence_records where mailbox_id = ? order by shard_id, evidence_id", (mailbox_id,)).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def write_shard(index_dir: Path, conn: sqlite3.Connection, mailbox_id: str, shard_id: str) -> None:
    records = load_records(conn, mailbox_id, shard_id)
    shard_dir = index_dir / "shards" / Path(shard_id)
    atomic_write_text(shard_dir / "evidence.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    threads = build_thread_records(records)
    atomic_write_text(shard_dir / "threads.jsonl", "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in threads))
    manifest = {"mailbox_id": mailbox_id, "shard_id": shard_id, "record_count": len(records), "thread_count": len(threads), "generated_at": now(), "indexer_version": PARSER_VERSION}
    atomic_write_text(shard_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))


def write_thread_index(index_dir: Path, mailbox_id: str, records: List[Dict[str, Any]], threads: List[Dict[str, Any]]) -> None:
    rollup = index_dir / "rollups"
    rollup.mkdir(parents=True, exist_ok=True)
    target = rollup / "thread_index.sqlite"
    tmp = rollup / f"thread_index.sqlite.tmp.{os.getpid()}.{uuid.uuid4().hex}"
    conn = sqlite3.connect(tmp)
    try:
        conn.executescript("""
            create table evidence_locator (evidence_id text primary key, mailbox_id text not null, thread_id text not null, shard_id text not null, subject text, sent_at text, search_text text);
            create table threads (thread_id text primary key, mailbox_id text not null, subject text, participants_json text, started_at text, last_updated_at text, message_count integer, evidence_ids_json text, summary text, search_text text);
            create index idx_evidence_locator_thread on evidence_locator(thread_id);
            create index idx_threads_updated on threads(last_updated_at);
        """)
        for r in records:
            conn.execute("insert into evidence_locator values (?, ?, ?, ?, ?, ?, ?)", (r["evidence_id"], mailbox_id, r["thread_id"], r.get("shard_id", "unknown"), r.get("subject", ""), r.get("sent_at", ""), json.dumps(r, ensure_ascii=False).lower()))
        for t in threads:
            conn.execute("insert into threads values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (t["thread_id"], mailbox_id, t.get("subject", ""), json.dumps(t.get("participants", []), ensure_ascii=False), t.get("started_at", ""), t.get("last_updated_at", ""), int(t.get("message_count", 0)), json.dumps(t.get("evidence_ids", []), ensure_ascii=False), t.get("summary", ""), json.dumps(t, ensure_ascii=False).lower()))
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, target)


def publish_rollups(index_dir: Path, conn: sqlite3.Connection, mailbox_id: str) -> Dict[str, int]:
    records = load_records(conn, mailbox_id)
    threads = build_thread_records(records)
    people = Counter(); keywords = Counter(); attachments = Counter()
    for r in records:
        for field in ("sender", "recipients", "cc"):
            people.update(split_people(r.get(field, "")))
        keywords.update(r.get("keywords", [])); attachments.update(r.get("attachments", []))
    shard_count = len({r.get("shard_id", "unknown") for r in records})
    summary_text = f"Mailbox {mailbox_id} is indexed with the production sharded index. {len(records)} messages, {len(threads)} threads, {shard_count} shards."
    recent = sorted(records, key=lambda x: x.get("sent_at") or x.get("file_mtime") or "", reverse=True)[:30]
    summary = {"answer_basis": "server_index", "mailbox_id": mailbox_id, "summary": summary_text, "indexed_at": now(), "indexer_version": PARSER_VERSION, "message_count": len(records), "thread_count": len(threads), "shard_count": shard_count, "top_people": [{"name": k, "count": v} for k, v in people.most_common(30)], "top_keywords": [{"keyword": k, "count": v} for k, v in keywords.most_common(50)], "top_attachments": [{"name": k, "count": v} for k, v in attachments.most_common(30)], "recent_evidence": [{"evidence_id": r["evidence_id"], "thread_id": r["thread_id"], "subject": r.get("subject"), "sender": r.get("sender"), "sent_at": r.get("sent_at"), "shard_id": r.get("shard_id"), "keywords": r.get("keywords", [])} for r in recent]}
    atomic_write_text(index_dir / "rollups" / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
    atomic_write_text(index_dir / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
    atomic_write_text(index_dir / "summary.md", summary_text + "\n")
    atomic_write_text(index_dir / "threads.json", json.dumps(threads[:200], ensure_ascii=False, indent=2))
    write_thread_index(index_dir, mailbox_id, records, threads)
    return {"message_count": len(records), "thread_count": len(threads), "shard_count": shard_count}


def job_manifest_path(index_dir: Path, job_id: str) -> Path:
    return index_dir / "state" / "jobs" / f"{job_id}.json"


def create_job(conn: sqlite3.Connection, index_dir: Path, mailbox_id: str, job_type: str, group_keys: List[str]) -> str:
    job_id = "job_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    cursor = {"processed_groups": 0, "total_groups": len(group_keys)}
    atomic_write_text(job_manifest_path(index_dir, job_id), json.dumps({"job_id": job_id, "mailbox_id": mailbox_id, "job_type": job_type, "group_keys": group_keys, "created_at": now()}, ensure_ascii=False, indent=2))
    conn.execute("insert into index_jobs (job_id, mailbox_id, job_type, status, cursor, lease_owner, lease_expires_at, started_at, finished_at, error_message) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (job_id, mailbox_id, job_type, "running", json.dumps(cursor, ensure_ascii=False), f"pid:{os.getpid()}", "", now(), "", ""))
    conn.commit()
    return job_id


def load_job(conn: sqlite3.Connection, index_dir: Path, mailbox_id: str, job_id: str) -> Tuple[List[str], int]:
    row = conn.execute("select * from index_jobs where job_id = ? and mailbox_id = ?", (job_id, mailbox_id)).fetchone()
    if not row:
        raise RuntimeError(f"resume job not found: {job_id}")
    manifest = json.loads(job_manifest_path(index_dir, job_id).read_text(encoding="utf-8"))
    cursor = json.loads(row["cursor"] or "{}")
    return list(manifest.get("group_keys", [])), int(cursor.get("processed_groups", 0))


def update_job(conn: sqlite3.Connection, job_id: str, processed: int, total: int, status: str, error: str = "") -> None:
    finished = now() if status in {"succeeded", "failed"} else ""
    conn.execute("update index_jobs set status = ?, cursor = ?, lease_owner = ?, lease_expires_at = ?, finished_at = ?, error_message = ? where job_id = ?", (status, json.dumps({"processed_groups": processed, "total_groups": total}, ensure_ascii=False), f"pid:{os.getpid()}", "", finished, error, job_id))
    conn.commit()


def append_dead_letter(index_dir: Path, payload: Dict[str, Any]) -> None:
    path = index_dir / "state" / "dead_letter.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def plan_groups(conn: sqlite3.Connection, mailbox_id: str, mailbox_root: Path, candidates: List[str], run_id: str, full_scan: bool) -> Dict[str, Any]:
    groups: Dict[str, Path] = {}; affected: Set[str] = set(); seen: Set[str] = set(); skipped = 0; deleted = 0
    for rel in candidates:
        if not rel or rel in seen:
            continue
        seen.add(rel); path = rel_path(mailbox_root, rel); row = state_row(conn, mailbox_id, rel)
        if path.is_file():
            size, mtime = file_sig(path)
            if row and row["status"] == "indexed" and row["file_size"] == size and row["mtime_ns"] == mtime and row["parser_version"] == PARSER_VERSION:
                skipped += 1
                if full_scan:
                    conn.execute("update indexed_files set last_seen_at = ?, run_id = ? where mailbox_id = ? and relative_path = ?", (now(), run_id, mailbox_id, rel))
                continue
            key, folder = message_key(mailbox_root, path); groups[key] = folder; continue
        if path.is_dir():
            groups[rel] = path; continue
        if row and row["status"] != "deleted":
            deleted += 1; old_key = row["message_key"] or rel
            if row["shard_id"]:
                affected.add(row["shard_id"])
            upsert_state(conn, mailbox_id, rel, "deleted", run_id, message_key_value=old_key, record_id=row["record_id"] or "", thread_id=row["thread_id"] or "", evidence_id=row["evidence_id"] or "", shard_id=row["shard_id"] or "", error_message="source file missing")
            folder = rel_path(mailbox_root, old_key)
            if folder.exists():
                groups[old_key] = folder
            else:
                affected.update(delete_records_for_message(conn, mailbox_id, old_key))
        else:
            skipped += 1
    if full_scan:
        for row in conn.execute("select relative_path, message_key, shard_id from indexed_files where mailbox_id = ? and status = 'indexed'", (mailbox_id,)).fetchall():
            if row["relative_path"] in seen:
                continue
            deleted += 1; old_key = row["message_key"] or row["relative_path"]
            if row["shard_id"]:
                affected.add(row["shard_id"])
            upsert_state(conn, mailbox_id, row["relative_path"], "deleted", run_id, message_key_value=old_key, shard_id=row["shard_id"] or "", error_message="source file missing during full scan")
            affected.update(delete_records_for_message(conn, mailbox_id, old_key))
    conn.commit()
    return {"groups": groups, "affected_shards": affected, "skipped_unchanged_file_count": skipped, "deleted_file_count": deleted, "candidate_file_count": len(seen)}


def process_group_v4(conn: sqlite3.Connection, mailbox_id: str, mailbox_root: Path, key: str, run_id: str) -> Tuple[Set[str], int]:
    affected = delete_records_for_message(conn, mailbox_id, key)
    group, skipped = collect_group_v4(mailbox_root, key)
    rec = group_to_record(mailbox_id, mailbox_root, key, group)
    shard = ""; pub: Optional[Dict[str, Any]] = None
    if rec:
        shard = shard_id_for_record(rec); pub = public_record(rec, shard); affected.add(shard)
        conn.execute("insert into evidence_records (mailbox_id, evidence_id, message_key, thread_id, shard_id, record_json, updated_at, run_id) values (?, ?, ?, ?, ?, ?, ?, ?) on conflict(evidence_id) do update set message_key = excluded.message_key, thread_id = excluded.thread_id, shard_id = excluded.shard_id, record_json = excluded.record_json, updated_at = excluded.updated_at, run_id = excluded.run_id", (mailbox_id, pub["evidence_id"], key, pub["thread_id"], shard, json.dumps(pub, ensure_ascii=False), now(), run_id))
    for rel in sorted(set(group.get("all_files", []))):
        path = rel_path(mailbox_root, rel)
        if path.is_file():
            size, mtime = file_sig(path)
            upsert_state(conn, mailbox_id, rel, "indexed", run_id, file_size=size, mtime_ns=mtime, message_key_value=key, record_id=pub["message_id"] if pub else "", thread_id=pub["thread_id"] if pub else "", evidence_id=pub["evidence_id"] if pub else "", shard_id=shard)
    conn.commit()
    return affected, skipped


def fail_group(conn: sqlite3.Connection, index_dir: Path, mailbox_id: str, mailbox_root: Path, key: str, run_id: str, exc: Exception) -> None:
    folder = rel_path(mailbox_root, key)
    files = [folder] if folder.is_file() else list(iter_files(folder)) if folder.is_dir() else []
    for path in files:
        rel = path.relative_to(mailbox_root).as_posix(); size, mtime = file_sig(path)
        upsert_state(conn, mailbox_id, rel, "failed", run_id, file_size=size, mtime_ns=mtime, message_key_value=key, error_message=str(exc)[:1000])
    append_dead_letter(index_dir, {"ts": now(), "mailbox_id": mailbox_id, "message_key": key, "error": str(exc), "run_id": run_id, "parser_version": PARSER_VERSION})
    conn.commit()


def write_status(index_dir: Path, payload: Dict[str, Any]) -> None:
    atomic_write_text(index_dir / "index_status.json", json.dumps(payload, ensure_ascii=False, indent=2))


def build_mailbox(mailbox_id: str, *, changed_list: Optional[Path] = None, resume_job_id: Optional[str] = None, job_type: Optional[str] = None, max_groups: Optional[int] = None) -> Dict[str, Any]:
    mailbox_root = safe_child(RAW_ROOT, mailbox_id); index_dir = safe_child(INDEX_ROOT, mailbox_id); index_dir.mkdir(parents=True, exist_ok=True)
    run_id = "run_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    if not mailbox_root.exists():
        status = {"mailbox_id": mailbox_id, "status": "raw_missing", "indexed_at": now(), "raw_root": str(mailbox_root)}; write_status(index_dir, status); return status
    conn = connect_state(index_dir)
    affected: Set[str] = set(); skipped_unchanged = deleted = candidates = skipped_files = failed_groups = processed_now = 0; status_value = "ready"
    try:
        if resume_job_id:
            group_keys, start_at = load_job(conn, index_dir, mailbox_id, resume_job_id); job_id = resume_job_id; effective_job_type = job_type or "repair"
        else:
            full_scan = changed_list is None; candidate_paths = load_changed_paths(mailbox_root, changed_list)
            plan = plan_groups(conn, mailbox_id, mailbox_root, candidate_paths, run_id, full_scan)
            group_keys = sorted(plan["groups"].keys()); start_at = 0; affected.update(plan["affected_shards"])
            skipped_unchanged = int(plan["skipped_unchanged_file_count"]); deleted = int(plan["deleted_file_count"]); candidates = int(plan["candidate_file_count"])
            effective_job_type = job_type or ("backfill" if full_scan else "incremental")
            job_id = create_job(conn, index_dir, mailbox_id, effective_job_type, group_keys)
        total = len(group_keys); cursor = start_at; limit = max_groups if max_groups and max_groups > 0 else None
        for key in group_keys[start_at:]:
            if limit is not None and processed_now >= limit:
                status_value = "partial"; break
            try:
                shards, skipped = process_group_v4(conn, mailbox_id, mailbox_root, key, run_id); affected.update(shards); skipped_files += skipped
            except Exception as exc:
                failed_groups += 1; fail_group(conn, index_dir, mailbox_id, mailbox_root, key, run_id, exc)
            processed_now += 1; cursor += 1; update_job(conn, job_id, cursor, total, "running")
        update_job(conn, job_id, cursor, total, "running" if status_value == "partial" else "succeeded")
        for shard in sorted(affected):
            write_shard(index_dir, conn, mailbox_id, shard)
        rollup = publish_rollups(index_dir, conn, mailbox_id)
        failed_files = conn.execute("select count(*) as c from indexed_files where mailbox_id = ? and status = 'failed'", (mailbox_id,)).fetchone()["c"]
        status = {"mailbox_id": mailbox_id, "status": status_value, "indexed_at": now(), "indexer_version": PARSER_VERSION, "raw_root": str(mailbox_root), "index_root": str(index_dir), "job_id": job_id, "job_type": effective_job_type, "run_id": run_id, "candidate_file_count": candidates, "planned_group_count": total, "processed_group_count": processed_now, "skipped_unchanged_file_count": skipped_unchanged, "skipped_file_count": skipped_files, "deleted_file_count": deleted, "failed_group_count": failed_groups, "failed_file_count": int(failed_files), **rollup}
        write_status(index_dir, status); return status
    except Exception as exc:
        if "job_id" in locals():
            update_job(conn, job_id, 0, 0, "failed", str(exc)[:1000])
        status = {"mailbox_id": mailbox_id, "status": "error", "error": str(exc), "indexed_at": now(), "indexer_version": PARSER_VERSION}; write_status(index_dir, status); return status
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mailboxes", nargs="*", help="Mailbox ids to index. Defaults to all first-level raw dirs.")
    parser.add_argument("--changed-list", type=Path, help="Text file containing changed relative paths for incremental indexing.")
    parser.add_argument("--resume-job-id", help="Resume a previous job using its saved checkpoint manifest.")
    parser.add_argument("--job-type", choices=["backfill", "incremental", "compact", "repair"], help="Job type written to index_jobs.")
    parser.add_argument("--max-groups", type=int, help="Process at most this many message groups, leaving the job resumable.")
    args = parser.parse_args()
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    mailboxes = args.mailboxes or sorted(p.name for p in RAW_ROOT.iterdir() if p.is_dir())
    results = []
    for mailbox_id in mailboxes:
        print(f"[{now()}] indexing {mailbox_id} ...", flush=True)
        result = build_mailbox(mailbox_id, changed_list=args.changed_list, resume_job_id=args.resume_job_id, job_type=args.job_type, max_groups=args.max_groups)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        results.append(result)
    atomic_write_text(INDEX_ROOT / "latest_batch_status.json", json.dumps({"generated_at": now(), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()