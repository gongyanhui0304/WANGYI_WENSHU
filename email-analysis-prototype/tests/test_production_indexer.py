import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEXER = ROOT / "mcp-server" / "server" / "mail_indexer.py"
API = ROOT / "mcp-server" / "server" / "mail_http_api.py"


def write_eml(path: Path, subject: str, body: str, date: str = "Fri, 04 Jul 2026 10:30:00 +0800") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "From: alice@example.com",
                "To: bob@example.com",
                f"Date: {date}",
                f"Subject: {subject}",
                "",
                body,
            ]
        ),
        encoding="utf-8",
    )




def write_ics(path: Path, summary: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "BEGIN:VCALENDAR",
                "BEGIN:VEVENT",
                "DTSTART:20260704T110000Z",
                "DTSTAMP:20260704T100000Z",
                "ORGANIZER:mailto:alice@example.com",
                "ATTENDEE:mailto:bob@example.com",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                "END:VEVENT",
                "END:VCALENDAR",
            ]
        ),
        encoding="utf-8",
    )
def load_api_module(env: dict[str, str]):
    old_env = os.environ.copy()
    os.environ.update(env)
    try:
        name = "mail_http_api_under_test_" + next(tempfile._get_candidate_names())
        spec = importlib.util.spec_from_file_location(name, API)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        os.environ.clear()
        os.environ.update(old_env)


class ProductionIndexerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw_root = self.root / "raw"
        self.index_root = self.root / "index"
        self.log_root = self.root / "logs"
        self.mailbox = "box_a"
        self.env = os.environ.copy()
        self.env.update(
            {
                "MAIL_RAW_ROOT": str(self.raw_root),
                "MAIL_INDEX_ROOT": str(self.index_root),
                "MAIL_LOG_ROOT": str(self.log_root),
                "MAIL_INDEX_MAX_EVIDENCE": "1000",
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_indexer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INDEXER), *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def changed_list(self, *relative_paths: str) -> Path:
        path = self.root / "changed.txt"
        path.write_text("\n".join(relative_paths) + "\n", encoding="utf-8")
        return path

    def status(self) -> dict:
        return json.loads((self.index_root / self.mailbox / "index_status.json").read_text(encoding="utf-8"))

    def state_rows(self, table: str) -> list[sqlite3.Row]:
        db = self.index_root / self.mailbox / "state" / "indexed_files.sqlite"
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            return conn.execute(f"select * from {table}").fetchall()
        finally:
            conn.close()

    def test_changed_list_indexes_only_changed_files_into_state_and_shards(self) -> None:
        rel = "2026/07/streamview/message.eml"
        write_eml(
            self.raw_root / self.mailbox / rel,
            "StreamView project progress",
            "StreamView payment approval moved forward.",
        )

        result = self.run_indexer("--changed-list", str(self.changed_list(rel)), self.mailbox)

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        status = self.status()
        self.assertEqual(status["indexer_version"], "v4-production-sharded")
        self.assertEqual(status["message_count"], 1)
        self.assertEqual(status["processed_group_count"], 1)
        self.assertEqual(status["skipped_unchanged_file_count"], 0)

        indexed = self.state_rows("indexed_files")
        self.assertEqual(len(indexed), 1)
        self.assertEqual(indexed[0]["relative_path"], rel)
        self.assertEqual(indexed[0]["status"], "indexed")
        self.assertEqual(indexed[0]["shard_id"], "2026/07")

        shard = self.index_root / self.mailbox / "shards" / "2026" / "07" / "evidence.jsonl"
        records = [json.loads(line) for line in shard.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["subject"], "StreamView project progress")
        self.assertNotIn("raw_path", records[0])

        second = self.run_indexer("--changed-list", str(self.changed_list(rel)), self.mailbox)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        status = self.status()
        self.assertEqual(status["processed_group_count"], 0)
        self.assertEqual(status["skipped_unchanged_file_count"], 1)


    def test_flat_eml_and_ics_files_are_indexed_as_individual_messages(self) -> None:
        rel_one = "inbox/one.eml"
        rel_two = "inbox/two.eml"
        rel_three = "send/meeting.ics"
        write_eml(self.raw_root / self.mailbox / rel_one, "First flat inbox message", "first inbox body")
        write_eml(self.raw_root / self.mailbox / rel_two, "Second flat inbox message", "second inbox body")
        write_ics(self.raw_root / self.mailbox / rel_three, "Calendar flat message", "calendar body")

        result = self.run_indexer("--changed-list", str(self.changed_list(rel_one, rel_two, rel_three)), self.mailbox)

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        status = self.status()
        self.assertEqual(status["message_count"], 3)
        self.assertEqual(status["processed_group_count"], 3)
        indexed = self.state_rows("indexed_files")
        message_keys = {row["relative_path"]: row["message_key"] for row in indexed}
        self.assertEqual(message_keys[rel_one], rel_one)
        self.assertEqual(message_keys[rel_two], rel_two)
        self.assertEqual(message_keys[rel_three], rel_three)

        subjects = {json.loads(row["record_json"])["subject"] for row in self.state_rows("evidence_records")}
        self.assertIn("First flat inbox message", subjects)
        self.assertIn("Second flat inbox message", subjects)
        self.assertIn("Calendar flat message", subjects)
    def test_deleted_changed_file_removes_record_and_marks_tombstone(self) -> None:
        rel = "2026/07/streamview/message.eml"
        msg = self.raw_root / self.mailbox / rel
        write_eml(msg, "StreamView deletion case", "This message will be deleted.")
        self.assertEqual(self.run_indexer("--changed-list", str(self.changed_list(rel)), self.mailbox).returncode, 0)

        msg.unlink()
        result = self.run_indexer("--changed-list", str(self.changed_list(rel)), self.mailbox)

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        status = self.status()
        self.assertEqual(status["message_count"], 0)
        self.assertEqual(status["deleted_file_count"], 1)
        indexed = self.state_rows("indexed_files")
        self.assertEqual(indexed[0]["status"], "deleted")
        shard = self.index_root / self.mailbox / "shards" / "2026" / "07" / "evidence.jsonl"
        self.assertEqual(shard.read_text(encoding="utf-8"), "")

    def test_resume_job_continues_from_checkpoint(self) -> None:
        rel_one = "2026/07/one/message.eml"
        rel_two = "2026/07/two/message.eml"
        write_eml(self.raw_root / self.mailbox / rel_one, "First resumable message", "first body")
        write_eml(self.raw_root / self.mailbox / rel_two, "Second resumable message", "second body")

        first = self.run_indexer("--changed-list", str(self.changed_list(rel_one, rel_two)), "--max-groups", "1", self.mailbox)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        partial = self.status()
        self.assertEqual(partial["status"], "partial")
        self.assertEqual(partial["processed_group_count"], 1)
        job_id = partial["job_id"]

        resumed = self.run_indexer("--resume-job-id", job_id, self.mailbox)

        self.assertEqual(resumed.returncode, 0, resumed.stderr + resumed.stdout)
        status = self.status()
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["message_count"], 2)
        jobs = self.state_rows("index_jobs")
        self.assertEqual(jobs[-1]["status"], "succeeded")
        self.assertIn('"processed_groups": 2', jobs[-1]["cursor"])

    def test_http_api_reads_rollup_thread_index_and_sharded_evidence(self) -> None:
        rel = "2026/07/streamview/message.eml"
        write_eml(
            self.raw_root / self.mailbox / rel,
            "StreamView API lookup",
            "StreamView risk review and payment approval are both visible.",
        )
        result = self.run_indexer("--changed-list", str(self.changed_list(rel)), self.mailbox)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        api = load_api_module(self.env)
        user = {"allowed_mailboxes": [self.mailbox], "permissions": ["read_evidence"]}

        summary = api.query_summary(user, {"mailbox_id": self.mailbox, "query": "StreamView"})
        self.assertEqual(summary["answer_basis"], "server_index")
        self.assertEqual(summary["message_count"], 1)
        self.assertEqual(summary["indexer_version"], "v4-production-sharded")

        threads = api.search_threads(user, {"mailbox_id": self.mailbox, "query": "StreamView"})
        self.assertEqual(len(threads["threads"]), 1)
        evidence_id = threads["threads"][0]["evidence_ids"][0]

        evidence = api.get_evidence(user, {"mailbox_id": self.mailbox, "evidence_id": evidence_id})
        self.assertEqual(len(evidence["evidence"]), 1)
        self.assertEqual(evidence["evidence"][0]["evidence_id"], evidence_id)
        self.assertIn("payment approval", evidence["evidence"][0]["excerpt"])
        self.assertNotIn("raw_path", evidence["evidence"][0])


if __name__ == "__main__":
    unittest.main()
