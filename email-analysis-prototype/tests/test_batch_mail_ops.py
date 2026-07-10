import json
import os
import tempfile
import unittest
from pathlib import Path

from mcp_server_path import load_batch_ops


batch_ops = load_batch_ops()


class BatchMailOpsTest(unittest.TestCase):
    def test_discover_two_level_department_mailboxes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "caigou" / "hqsc_gd3" / "inbox").mkdir(parents=True)
            (root / "caigou" / "hqsc_gd3" / "inbox" / "a.eml").write_text("Subject: A", encoding="utf-8")
            (root / "caigou" / "not_mailbox").mkdir(parents=True)
            (root / "yingxiao" / "yx_001" / "send").mkdir(parents=True)
            (root / "yingxiao" / "yx_001" / "send" / "b.ics").write_text("BEGIN:VCALENDAR", encoding="utf-8")

            found = batch_ops.discover_mailboxes(root, ["caigou", "yingxiao"])

            self.assertEqual(found, ["caigou/hqsc_gd3", "yingxiao/yx_001"])

    def test_changed_list_detects_new_changed_and_deleted_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw = base / "raw"
            index = base / "index"
            logs = base / "logs"
            inbox = raw / "caigou" / "hqsc_gd3" / "inbox"
            inbox.mkdir(parents=True)
            keep = inbox / "keep.eml"
            remove = inbox / "remove.eml"
            keep.write_text("Subject: old", encoding="utf-8")
            remove.write_text("Subject: remove", encoding="utf-8")

            mailbox_id = "caigou/hqsc_gd3"
            current = {
                "inbox/keep.eml": batch_ops.file_signature(keep),
                "inbox/remove.eml": batch_ops.file_signature(remove),
            }
            batch_ops.save_manifest(index, mailbox_id, current)

            keep.write_text("Subject: changed", encoding="utf-8")
            remove.unlink()
            new_file = inbox / "new.eml"
            new_file.write_text("Subject: new", encoding="utf-8")

            changed_path, summary, new_manifest = batch_ops.build_changed_list(raw, index, logs, mailbox_id)
            changed = changed_path.read_text(encoding="utf-8").splitlines()

            self.assertEqual(summary["changed_file_count"], 3)
            self.assertEqual(changed, ["inbox/keep.eml", "inbox/new.eml", "inbox/remove.eml"])
            self.assertIn("inbox/keep.eml", new_manifest)
            self.assertIn("inbox/new.eml", new_manifest)
            self.assertNotIn("inbox/remove.eml", new_manifest)


if __name__ == "__main__":
    unittest.main()
