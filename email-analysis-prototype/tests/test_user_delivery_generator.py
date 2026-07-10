import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "client" / "generate_user_delivery.mjs"


def node_binary() -> str:
    candidates = [
        shutil.which("node"),
        r"C:\Program Files\nodejs\node.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError("node executable not found")


class UserDeliveryGeneratorTest(unittest.TestCase):
    def test_delivery_bundle_has_platform_config_and_per_user_bridge(self) -> None:
        user_id = "delivery_test"
        out_dir = ROOT / "dist" / "platform-delivery" / user_id
        if out_dir.exists():
            shutil.rmtree(out_dir)

        result = subprocess.run(
            [
                node_binary(),
                str(GENERATOR),
                "--user-id",
                user_id,
                "--mcp-url",
                "https://mail-analysis.example.com/mcp",
                "--token",
                "test-token",
                "--mailbox",
                "caigou/hqsc_gd3",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["delivery_mode"], "platform_managed_stdio_bridge_with_embedded_remote_mcp")
        self.assertFalse(payload["user_side_manual_config_required"])
        self.assertEqual(
            payload["platform_admin_files"],
            [
                "platform-admin/PLATFORM_ADMIN_SETUP.md",
                "platform-admin/mcp-registration.json",
                "platform-admin/remote-mcp-registration.json",
            ],
        )
        self.assertEqual(
            payload["user_files"],
            ["user/email_mcp_stdio.mjs", "user/SKILL.md", "user-test/USER_TEST_PROMPT.md"],
        )

        platform_config = json.loads((out_dir / "platform-admin" / "mcp-registration.json").read_text(encoding="utf-8"))
        self.assertEqual(platform_config["name"], "emailProjectAnalysis")
        self.assertEqual(platform_config["command"], "node")
        self.assertEqual(
            platform_config["args"],
            [r"C:\email-mcp\delivery_test\email_mcp_stdio.mjs"],
        )
        remote_config = json.loads((out_dir / "platform-admin" / "remote-mcp-registration.json").read_text(encoding="utf-8"))
        self.assertEqual(remote_config["transport"], "streamable-http")
        self.assertEqual(remote_config["url"], "https://mail-analysis.example.com/mcp")
        self.assertEqual(remote_config["headers"]["Authorization"], "Bearer test-token")

        bridge = (out_dir / "user" / "email_mcp_stdio.mjs").read_text(encoding="utf-8")
        self.assertIn('const EMBEDDED_MCP_URL = "https://mail-analysis.example.com/mcp";', bridge)
        self.assertIn('const EMBEDDED_TOKEN = "test-token";', bridge)

        skill_doc = (out_dir / "user" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("emailProjectAnalysis", skill_doc)
        self.assertIn("Workspace fallback", skill_doc)
        self.assertIn("node ./email_mcp_stdio.mjs list_mailboxes", skill_doc)
        self.assertIn("Never ask the user for a token", skill_doc)

        admin_doc = (out_dir / "platform-admin" / "PLATFORM_ADMIN_SETUP.md").read_text(encoding="utf-8")
        self.assertIn("Preferred: Remote MCP", admin_doc)
        self.assertIn("command: node", admin_doc)
        self.assertIn(r"C:\email-mcp\delivery_test\email_mcp_stdio.mjs", admin_doc)
        self.assertIn("Never share one user's registration", admin_doc)

        user_doc = (out_dir / "user-test" / "USER_TEST_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("The user does not configure MCP", user_doc)
        self.assertIn("list_mailboxes is unavailable", user_doc)
        self.assertIn("caigou/hqsc_gd3", user_doc)

        shutil.rmtree(out_dir)


if __name__ == "__main__":
    unittest.main()
