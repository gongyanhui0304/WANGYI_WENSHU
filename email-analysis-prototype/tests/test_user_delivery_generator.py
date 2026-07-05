import json
import os
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
    def test_delivery_bundle_splits_user_files_from_it_install_files(self) -> None:
        user_id = "delivery_test"
        out_dir = ROOT / "dist" / "user-delivery" / user_id
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
        self.assertEqual(
            payload["user_files"],
            ["user/email_mcp_stdio.mjs", "user/SKILL.md"],
        )
        self.assertEqual(
            payload["it_files"],
            ["it/IT_INSTALL.md", "it/mcp-config.codex.toml", "it/mcp-config.generic.json"],
        )
        self.assertEqual(
            sorted(p.name for p in (out_dir / "user").iterdir()),
            ["SKILL.md", "email_mcp_stdio.mjs"],
        )

        install = (out_dir / "it" / "IT_INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("文件放进工作区不会自动加载 MCP", install)
        self.assertIn("最终用户不需要手动提醒智能体读取 mjs 或 Skill", install)
        self.assertIn("emailProjectAnalysis", install)
        self.assertIn("../user/email_mcp_stdio.mjs", install)

        codex = (out_dir / "it" / "mcp-config.codex.toml").read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.emailProjectAnalysis]", codex)
        self.assertIn("../user/email_mcp_stdio.mjs", codex)

        generic = json.loads((out_dir / "it" / "mcp-config.generic.json").read_text(encoding="utf-8"))
        self.assertEqual(generic["mcpServers"]["emailProjectAnalysis"]["command"], "node")
        self.assertIn("../user/email_mcp_stdio.mjs", generic["mcpServers"]["emailProjectAnalysis"]["args"][0])

        shutil.rmtree(out_dir)


if __name__ == "__main__":
    unittest.main()
