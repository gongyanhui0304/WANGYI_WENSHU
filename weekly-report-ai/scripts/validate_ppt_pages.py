"""Validate PPT page contracts under ppt/pages.

Each page folder is the source of truth. A page is invalid if config.json,
page.md, notes.md, or example.png is missing or inconsistent.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PAGES = BASE / "ppt" / "pages"
REQUIRED_PAGE_SECTIONS = [
    "## 页面目标",
    "## 页面类型",
    "## 禁止事项",
    "## 输出要求",
    "## 验收标准",
]
REQUIRED_NOTE_SECTIONS = [
    "## 文件职责",
    "## 维护注意事项",
    "## 本页特殊说明",
    "## 后续待办",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def page_no_from_dir(path: Path) -> int:
    match = re.match(r"^(\d+)_", path.name)
    if not match:
        raise ValueError(f"页面目录必须以数字开头: {path.name}")
    return int(match.group(1))


def validate() -> list[str]:
    errors: list[str] = []
    page_dirs = sorted([p for p in PAGES.iterdir() if p.is_dir()])
    expected = 1
    for page_dir in page_dirs:
        try:
            dir_no = page_no_from_dir(page_dir)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if dir_no != expected:
            errors.append(f"页面编号不连续: {page_dir.name}, expected {expected:02d}")
        expected += 1

        config_path = page_dir / "config.json"
        page_md = page_dir / "page.md"
        notes_md = page_dir / "notes.md"
        example_png = page_dir / "example.png"
        for required in [config_path, page_md, notes_md, example_png]:
            if not required.exists():
                errors.append(f"缺少文件: {required}")
            elif required.stat().st_size <= 0:
                errors.append(f"文件为空: {required}")
        if not config_path.exists():
            continue
        try:
            config = load_json(config_path)
        except Exception as exc:
            errors.append(f"config.json 非法: {config_path}: {exc}")
            continue
        if config.get("page") != dir_no:
            errors.append(f"page 不匹配: {page_dir.name} config.page={config.get('page')}")
        if not config.get("type"):
            errors.append(f"缺少 type: {config_path}")
        if config.get("visual_reference") != "example.png":
            errors.append(f"visual_reference 必须为 example.png: {config_path}")
        if config.get("standard_ref") != "ppt/spec/page_standard.md":
            errors.append(f"standard_ref 必须为 ppt/spec/page_standard.md: {config_path}")
        if page_md.exists():
            text = page_md.read_text(encoding="utf-8-sig")
            for section in REQUIRED_PAGE_SECTIONS:
                if section not in text:
                    errors.append(f"{page_md} 缺少章节 {section}")
        if notes_md.exists():
            text = notes_md.read_text(encoding="utf-8-sig")
            for section in REQUIRED_NOTE_SECTIONS:
                if section not in text:
                    errors.append(f"{notes_md} 缺少章节 {section}")
    return errors


if __name__ == "__main__":
    problems = validate()
    if problems:
        print("PPT page contract validation failed:")
        for problem in problems:
            print(f"- {problem}")
        sys.exit(1)
    print("PPT page contract validation passed.")
