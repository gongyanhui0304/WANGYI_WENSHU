import importlib.util
from pathlib import Path


def load_batch_ops():
    root = Path(__file__).resolve().parents[1]
    path = root / "mcp-server" / "server" / "batch_mail_ops.py"
    spec = importlib.util.spec_from_file_location("batch_mail_ops", str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
