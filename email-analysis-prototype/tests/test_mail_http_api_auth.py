import importlib.util
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_DATA = ROOT / "tests" / ".mail-http-api-auth"
os.environ.setdefault("MAIL_RAW_ROOT", str(TEST_DATA / "raw"))
os.environ.setdefault("MAIL_INDEX_ROOT", str(TEST_DATA / "index"))
os.environ.setdefault("MAIL_LOG_ROOT", str(TEST_DATA / "logs"))
os.environ.setdefault("MAIL_PERMISSIONS_FILE", str(TEST_DATA / "permissions.json"))

MODULE_PATH = ROOT / "mcp-server" / "server" / "mail_http_api.py"
SPEC = importlib.util.spec_from_file_location("mail_http_api", MODULE_PATH)
mail_http_api = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mail_http_api)


class McpAuthenticationScopeTest(unittest.TestCase):
    def test_discovery_methods_are_public(self) -> None:
        for method in ("initialize", "notifications/initialized", "ping", "tools/list"):
            with self.subTest(method=method):
                payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {}}
                self.assertFalse(mail_http_api._mcp_payload_requires_auth(payload))

    def test_tool_calls_require_authentication(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "list_mailboxes", "arguments": {}},
        }
        self.assertTrue(mail_http_api._mcp_payload_requires_auth(payload))

    def test_batch_requires_auth_if_any_message_is_protected(self) -> None:
        payload = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {}},
        ]
        self.assertTrue(mail_http_api._mcp_payload_requires_auth(payload))


if __name__ == "__main__":
    unittest.main()