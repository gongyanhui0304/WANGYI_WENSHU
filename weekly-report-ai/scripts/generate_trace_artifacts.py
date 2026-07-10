"""Build trace artifacts for PPT pages before generation.

This is the audit gate for PPT generation. It reads ppt/pages/<page>/config.json,
executes the configured metric queries, and writes both run-level metric
artifacts and page-level debug artifacts.

The runner fails closed: if a page declares metrics but does not map them to a
trace source, or if SQL still contains unresolved template placeholders, PPT
generation must stop.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
PAGES = BASE / "ppt" / "pages"
METRIC_MASTER = BASE / "metrics" / "metric_registry.json"
METRIC_ROOT = BASE / "data" / "metrics"
OUTPUT_DEBUG = BASE / "output" / "debug"


@dataclass
class TraceError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def safe_name(value: str) -> str:
    value = str(value).strip().replace(" ", "_")
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    return value or "metric"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def week_context(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return {
        "today": today.isoformat(),
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "iso_week": today.isocalendar().week,
        "date_range": f"{monday.year}.{monday.month}.{monday.day}-{sunday.year}.{sunday.month}.{sunday.day}",
    }


def page_dirs() -> list[Path]:
    return sorted(p for p in PAGES.iterdir() if p.is_dir())


def metric_master_index() -> dict[str, dict[str, Any]]:
    data = load_json(METRIC_MASTER)
    return {item["metric_id"]: item for item in data.get("metrics", [])}


def unresolved_placeholders(sql: str) -> list[str]:
    patterns = []
    if "${" in sql:
        patterns.append("${...}")
    if "{[" in sql or "}]}" in sql:
        patterns.append("{[...]} SmartBI macro")
    return patterns


def redmine_params() -> dict[str, Any]:
    ctx = week_context()
    return {"week_start": ctx["week_start"], "week_end": ctx["week_end"]}


def normalize_redmine_sql(sql: str) -> str:
    return sql.replace(":week_start", "%(week_start)s").replace(":week_end", "%(week_end)s")


SOURCE_HEALTH: dict[str, str | None] = {}


def assert_source_available(source: str) -> None:
    if source in SOURCE_HEALTH:
        cached = SOURCE_HEALTH[source]
        if cached:
            raise TraceError(cached)
        return

    if source == "redmine_postgres":
        from app.db.postgres import PostgresClient

        client = PostgresClient()
        if not client.is_configured:
            SOURCE_HEALTH[source] = "Redmine PostgreSQL 未配置"
            raise TraceError(SOURCE_HEALTH[source])
        result = client.test_connection()
        if not result.get("success"):
            SOURCE_HEALTH[source] = "Redmine PostgreSQL 连接失败，请检查 .env、网络、账号、驱动和数据库白名单"
            raise TraceError(SOURCE_HEALTH[source])
        SOURCE_HEALTH[source] = None
        return

    if source == "smartbi_sqlserver":
        from app.db.sqlserver import SQLServerClient

        client = SQLServerClient()
        if not client.is_configured:
            SOURCE_HEALTH[source] = "SmartBI SQL Server 未配置"
            raise TraceError(SOURCE_HEALTH[source])
        result = client.test_connection()
        if not result.get("success"):
            SOURCE_HEALTH[source] = "SmartBI SQL Server 连接失败，请检查 .env、网络、账号、ODBC 驱动和数据库白名单"
            raise TraceError(SOURCE_HEALTH[source])
        SOURCE_HEALTH[source] = None
        return

    raise TraceError(f"不支持的 SQL 数据源: {source}")


def execute_sql(source: str, sql: str) -> tuple[pd.DataFrame, int]:
    placeholders = unresolved_placeholders(sql)
    if placeholders:
        raise TraceError(f"SQL 存在未解析模板变量: {', '.join(placeholders)}")
    if not sql.strip():
        raise TraceError("SQL 文件为空")

    assert_source_available(source)
    started = time.perf_counter()
    if source == "redmine_postgres":
        from app.db.postgres import PostgresClient

        client = PostgresClient()
        df = client.execute_query(normalize_redmine_sql(sql), redmine_params())
    elif source == "smartbi_sqlserver":
        from app.db.sqlserver import SQLServerClient

        client = SQLServerClient()
        df = client.execute_query(sql)
    else:
        raise TraceError(f"不支持的 SQL 数据源: {source}")
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return df, elapsed_ms


def metric_value(df: pd.DataFrame, mode: str, field: str | None = None) -> Any:
    if mode == "row_count":
        return int(len(df))
    if mode == "first_cell":
        if df.empty or len(df.columns) == 0:
            return None
        value = df.iloc[0, 0]
        return value.item() if hasattr(value, "item") else value
    if mode == "sum_field":
        if not field or field not in df.columns:
            raise TraceError(f"sum_field 模式缺少字段或字段不存在: {field}")
        value = df[field].sum()
        return value.item() if hasattr(value, "item") else value
    if mode == "dataframe_rows":
        return int(len(df))
    raise TraceError(f"不支持的 value_mode: {mode}")


def write_metric_artifacts(
    *,
    run_dir: Path,
    page_debug_dir: Path,
    metric_id: str,
    metric_name: str,
    page: int,
    source: str,
    table: str,
    description: str,
    sql: str,
    df: pd.DataFrame,
    value: Any,
    sql_elapsed_ms: int,
    sql_execution_time: str,
) -> dict[str, Any]:
    metric_dir = run_dir / f"{metric_id}_{safe_name(metric_name)}"
    metric_dir.mkdir(parents=True, exist_ok=True)

    query_path = metric_dir / "query.sql"
    csv_path = metric_dir / "result.csv"
    json_path = metric_dir / "result.json"
    metric_path = metric_dir / "metric.json"
    summary_path = metric_dir / "summary.md"

    query_path.write_text(sql.strip() + "\n", encoding="utf-8")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_json(json_path, orient="records", force_ascii=False, indent=2, date_format="iso")

    rel = lambda p: str(p.relative_to(BASE)).replace("\\", "/")
    record = {
        "metric_id": metric_id,
        "metric_name": metric_name,
        "page": page,
        "source": source,
        "table": table,
        "description": description,
        "sql_execution_time": sql_execution_time,
        "generated_time": datetime.now().isoformat(timespec="seconds"),
        "sql_elapsed_ms": sql_elapsed_ms,
        "dataframe": f"DataFrame(rows={len(df)}, columns={list(df.columns)})",
        "csv": rel(csv_path),
        "json": rel(json_path),
        "sql": rel(query_path),
        "value": value,
        "row_count": int(len(df)),
        "ppt_refs": [f"page_{page:02d}"],
        "ai_analysis_refs": [f"output/debug/page_{page:02d}/ai_summary.md"],
    }
    metric_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    summary_path.write_text(
        "\n".join([
            f"# {metric_id} {metric_name}",
            "",
            f"- 指标值：{value}",
            f"- 数据源：{source}",
            f"- 统计口径：{description}",
            f"- SQL：{rel(query_path)}",
            f"- CSV：{rel(csv_path)}",
            f"- JSON：{rel(json_path)}",
            "",
            "## 追溯链路",
            "",
            f"PPT -> Metric {metric_id} -> query.sql -> result.csv/result.json -> 原始数据",
            "",
        ]),
        encoding="utf-8",
    )

    shutil.copy2(query_path, page_debug_dir / f"{metric_id}_query.sql")
    shutil.copy2(csv_path, page_debug_dir / f"{metric_id}_result.csv")
    shutil.copy2(json_path, page_debug_dir / f"{metric_id}_result.json")
    return record


def system_date_dataframe(metric_id: str) -> tuple[pd.DataFrame, str, Any]:
    ctx = week_context()
    if metric_id == "M101":
        value = f"{date.today().year}年 第{ctx['iso_week']}周"
        field = "week_label"
    elif metric_id == "M102":
        value = ctx["date_range"]
        field = "date_range"
    else:
        value = ctx.get(metric_id, "")
        field = "value"
    return pd.DataFrame([{field: value, **ctx}]), "-- SQL: 无。来源：SystemDate。", value


def registry_dataframe(metric_id: str, master: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, str, Any]:
    rows = list(master.values())
    df = pd.DataFrame(rows)
    if metric_id == "M301":
        value = len(rows)
        out = pd.DataFrame([{"registered_metric_count": value}])
    elif metric_id == "M302":
        metric_dirs = list(METRIC_ROOT.glob("*/*/result.csv")) if METRIC_ROOT.exists() else []
        value = len(metric_dirs)
        out = pd.DataFrame([{"csv_metric_count": value}])
    elif metric_id == "M303":
        metric_dirs = list(METRIC_ROOT.glob("*/*/result.json")) if METRIC_ROOT.exists() else []
        value = len(metric_dirs)
        out = pd.DataFrame([{"json_metric_count": value}])
    elif metric_id == "M304":
        generated = {p.parent.name.split("_", 1)[0] for p in METRIC_ROOT.glob("*/*/metric.json")} if METRIC_ROOT.exists() else set()
        value = len([m for m in rows if m.get("metric_id") not in generated])
        out = pd.DataFrame([{"pending_metric_count": value}])
    else:
        value = len(df)
        out = df
    return out, "-- SQL: 无。来源：MetricRegistry。", value


def build_trace_artifacts(run_id: str | None = None, *, strict: bool = True) -> Path:
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = METRIC_ROOT / safe_name(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    OUTPUT_DEBUG.mkdir(parents=True, exist_ok=True)

    master = metric_master_index()
    run_records: dict[str, Any] = {}
    errors: list[str] = []

    for page_dir in page_dirs():
        config = load_json(page_dir / "config.json")
        if config.get("enabled") is not True:
            continue
        page_no = int(config["page"])
        debug_dir = BASE / str(config.get("debug_output_dir", f"output/debug/page_{page_no:02d}"))
        debug_dir.mkdir(parents=True, exist_ok=True)
        log_lines = [
            f"page={page_dir.name}",
            f"started={datetime.now().isoformat(timespec='seconds')}",
            "trace_rule=all PPT numbers must resolve to Metric artifacts",
        ]
        page_records = []
        metric_queries = config.get("metric_queries") or {}
        metrics = config.get("metrics") or []

        for metric_id in metrics:
            try:
                query = metric_queries.get(metric_id)
                if not query:
                    raise TraceError(f"缺少 metric_queries.{metric_id}")
                meta = master.get(metric_id, {})
                metric_name = query.get("metric_name") or meta.get("metric_name") or metric_id
                source = query.get("source")
                sql_execution_time = datetime.now().isoformat(timespec="seconds")

                if source == "system_date":
                    df, sql, value = system_date_dataframe(metric_id)
                    elapsed_ms = 0
                    source_label = "SystemDate"
                elif source == "metric_registry":
                    df, sql, value = registry_dataframe(metric_id, master)
                    elapsed_ms = 0
                    source_label = "MetricRegistry"
                elif source in {"redmine_postgres", "smartbi_sqlserver"}:
                    sql_file = query.get("sql_file")
                    if not sql_file:
                        raise TraceError(f"{metric_id} 缺少 sql_file")
                    sql_path = BASE / sql_file
                    if not sql_path.exists():
                        raise TraceError(f"SQL 文件不存在: {sql_file}")
                    sql = sql_path.read_text(encoding="utf-8-sig")
                    df, elapsed_ms = execute_sql(source, sql)
                    value = metric_value(df, query.get("value_mode", "row_count"), query.get("value_field"))
                    source_label = "Redmine PostgreSQL" if source == "redmine_postgres" else "SmartBI SQL Server"
                else:
                    raise TraceError(f"{metric_id} 不支持或未声明 source")

                record = write_metric_artifacts(
                    run_dir=run_dir,
                    page_debug_dir=debug_dir,
                    metric_id=metric_id,
                    metric_name=metric_name,
                    page=page_no,
                    source=source_label,
                    table=query.get("table") or meta.get("table", ""),
                    description=query.get("description") or meta.get("description", ""),
                    sql=sql,
                    df=df,
                    value=value,
                    sql_elapsed_ms=elapsed_ms,
                    sql_execution_time=sql_execution_time,
                )
                page_records.append(record)
                run_records[metric_id] = record
                log_lines.append(f"OK {metric_id} value={value}")
            except Exception as exc:
                message = f"{page_dir.name} {metric_id}: {exc}"
                errors.append(message)
                log_lines.append(f"ERROR {message}")

        (debug_dir / "metrics.json").write_text(json.dumps(page_records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        (debug_dir / "ai_summary.md").write_text(
            "# AI分析\n\n未接入 AI 生成。任何分析必须引用本目录 metrics.json 中的 Metric。\n",
            encoding="utf-8",
        )
        log_lines.append(f"finished={datetime.now().isoformat(timespec='seconds')}")
        (debug_dir / "execution.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    registry_payload = {
        "run_id": run_dir.name,
        "generated_time": datetime.now().isoformat(timespec="seconds"),
        "strict": strict,
        "metrics": run_records,
        "errors": errors,
    }
    (run_dir / "registry.json").write_text(json.dumps(registry_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    if strict and errors:
        raise TraceError("追溯产物生成失败，禁止生成 PPT：\n" + "\n".join(f"- {e}" for e in errors))
    return run_dir


def main() -> None:
    try:
        run_dir = build_trace_artifacts(strict=True)
    except TraceError as exc:
        print(str(exc))
        sys.exit(1)
    print(f"Trace artifacts generated: {run_dir}")


if __name__ == "__main__":
    main()



