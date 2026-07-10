"""Metric registry and trace artifact writer.

Every number shown in generated PPT should be backed by a metric artifact folder:

    data/metrics/<run_id>/<metric_id>_<metric_name>/
        metric.json
        query.sql
        result.csv
        result.json
        summary.md

The registry keeps the chain SQL -> DataFrame -> CSV/JSON -> AI/PPT references explicit.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


@dataclass
class MetricRecord:
    metric_id: str
    metric_name: str
    page: int | list[int] | None
    source: str
    table: str
    description: str
    sql_execution_time: str
    generated_time: str
    sql_elapsed_ms: int
    dataframe: str
    csv: str
    json: str
    sql: str
    ai_analysis_refs: list[str] = field(default_factory=list)
    ppt_refs: list[str] = field(default_factory=list)
    value: Any = None
    row_count: int = 0


class MetricRegistry:
    """Write metric trace artifacts and a run-level registry.

    The class is intentionally small: scripts can adopt it gradually without
    changing PPT layout or business calculations.
    """

    def __init__(self, base_dir: str | Path, run_id: str | None = None):
        self.base_dir = Path(base_dir)
        self.run_id = self._safe_name(run_id or datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.run_dir = self.base_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, MetricRecord] = {}

    def count_rows(
        self,
        *,
        metric_id: str,
        metric_name: str,
        cursor: Any,
        sql: str,
        page: int | list[int] | None,
        source: str,
        table: str,
        description: str,
        ai_analysis_refs: Iterable[str] | None = None,
        ppt_refs: Iterable[str] | None = None,
    ) -> int:
        """Execute a detail SQL and use DataFrame row count as metric value."""
        df, started, elapsed_ms = self._execute_dataframe(cursor, sql)
        value = int(len(df))
        self._write_record(
            metric_id=metric_id,
            metric_name=metric_name,
            page=page,
            source=source,
            table=table,
            description=description,
            sql=sql,
            df=df,
            sql_execution_time=started,
            sql_elapsed_ms=elapsed_ms,
            value=value,
            ai_analysis_refs=list(ai_analysis_refs or []),
            ppt_refs=list(ppt_refs or []),
        )
        return value

    def query_value(
        self,
        *,
        metric_id: str,
        metric_name: str,
        cursor: Any,
        sql: str,
        page: int | list[int] | None,
        source: str,
        table: str,
        description: str,
        ai_analysis_refs: Iterable[str] | None = None,
        ppt_refs: Iterable[str] | None = None,
    ) -> Any:
        """Execute SQL and use the first cell as metric value."""
        df, started, elapsed_ms = self._execute_dataframe(cursor, sql)
        value = None if df.empty or len(df.columns) == 0 else df.iloc[0, 0]
        if hasattr(value, "item"):
            value = value.item()
        self._write_record(
            metric_id=metric_id,
            metric_name=metric_name,
            page=page,
            source=source,
            table=table,
            description=description,
            sql=sql,
            df=df,
            sql_execution_time=started,
            sql_elapsed_ms=elapsed_ms,
            value=value,
            ai_analysis_refs=list(ai_analysis_refs or []),
            ppt_refs=list(ppt_refs or []),
        )
        return value

    def query_dataframe(
        self,
        *,
        metric_id: str,
        metric_name: str,
        cursor: Any,
        sql: str,
        page: int | list[int] | None,
        source: str,
        table: str,
        description: str,
        ai_analysis_refs: Iterable[str] | None = None,
        ppt_refs: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Execute SQL and store the complete result as a trace artifact."""
        df, started, elapsed_ms = self._execute_dataframe(cursor, sql)
        self._write_record(
            metric_id=metric_id,
            metric_name=metric_name,
            page=page,
            source=source,
            table=table,
            description=description,
            sql=sql,
            df=df,
            sql_execution_time=started,
            sql_elapsed_ms=elapsed_ms,
            value=int(len(df)),
            ai_analysis_refs=list(ai_analysis_refs or []),
            ppt_refs=list(ppt_refs or []),
        )
        return df

    def record_manual(
        self,
        *,
        metric_id: str,
        metric_name: str,
        value: Any,
        page: int | list[int] | None,
        source: str,
        description: str,
        ppt_refs: Iterable[str] | None = None,
    ) -> Any:
        """Record a non-SQL value and mark it visibly as manual.

        This is allowed only for legacy constants while they are being migrated.
        New PPT metrics should use SQL-backed methods instead.
        """
        sql = "-- MANUAL LEGACY VALUE. Must be replaced by SQL-backed metric."
        df = pd.DataFrame([{"value": value, "trace_status": "manual_legacy"}])
        self._write_record(
            metric_id=metric_id,
            metric_name=metric_name,
            page=page,
            source=source,
            table="manual",
            description=description,
            sql=sql,
            df=df,
            sql_execution_time=datetime.now().isoformat(timespec="seconds"),
            sql_elapsed_ms=0,
            value=value,
            ppt_refs=list(ppt_refs or []),
        )
        return value

    def _execute_dataframe(self, cursor: Any, sql: str) -> tuple[pd.DataFrame, str, int]:
        started = datetime.now().isoformat(timespec="seconds")
        begin = time.perf_counter()
        cursor.execute(sql)
        rows = cursor.fetchall()
        elapsed_ms = int((time.perf_counter() - begin) * 1000)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        df = pd.DataFrame.from_records(rows, columns=columns)
        return df, started, elapsed_ms

    def _write_record(
        self,
        *,
        metric_id: str,
        metric_name: str,
        page: int | list[int] | None,
        source: str,
        table: str,
        description: str,
        sql: str,
        df: pd.DataFrame,
        sql_execution_time: str,
        sql_elapsed_ms: int,
        value: Any,
        ai_analysis_refs: list[str] | None = None,
        ppt_refs: list[str] | None = None,
    ) -> None:
        metric_dir = self.run_dir / f"{metric_id}_{self._safe_name(metric_name)}"
        metric_dir.mkdir(parents=True, exist_ok=True)

        query_path = metric_dir / "query.sql"
        csv_path = metric_dir / "result.csv"
        json_path = metric_dir / "result.json"
        metric_path = metric_dir / "metric.json"
        summary_path = metric_dir / "summary.md"

        query_path.write_text(sql.strip() + "\n", encoding="utf-8")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        df.to_json(json_path, orient="records", force_ascii=False, indent=2, date_format="iso")

        record = MetricRecord(
            metric_id=metric_id,
            metric_name=metric_name,
            page=page,
            source=source,
            table=table,
            description=description,
            sql_execution_time=sql_execution_time,
            generated_time=datetime.now().isoformat(timespec="seconds"),
            sql_elapsed_ms=sql_elapsed_ms,
            dataframe=f"DataFrame(rows={len(df)}, columns={list(df.columns)})",
            csv=str(csv_path.relative_to(self.base_dir.parent.parent)),
            json=str(json_path.relative_to(self.base_dir.parent.parent)),
            sql=str(query_path.relative_to(self.base_dir.parent.parent)),
            ai_analysis_refs=ai_analysis_refs or [],
            ppt_refs=ppt_refs or [],
            value=value,
            row_count=int(len(df)),
        )
        metric_path.write_text(
            json.dumps(record.__dict__, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        summary_path.write_text(self._summary(record), encoding="utf-8")
        self.records[metric_id] = record
        self.save_registry()

    def save_registry(self) -> None:
        payload = {
            "run_id": self.run_id,
            "generated_time": datetime.now().isoformat(timespec="seconds"),
            "rule": "Every PPT number must reference a Metric ID and source artifact.",
            "metrics": {k: v.__dict__ for k, v in sorted(self.records.items())},
        }
        (self.run_dir / "registry.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _summary(record: MetricRecord) -> str:
        return "\n".join(
            [
                f"# {record.metric_id} {record.metric_name}",
                "",
                f"- 指标值：{record.value}",
                f"- 数据源：{record.source}",
                f"- 表：{record.table}",
                f"- 统计口径：{record.description}",
                f"- SQL执行时间：{record.sql_execution_time}",
                f"- SQL耗时：{record.sql_elapsed_ms} ms",
                f"- DataFrame：{record.dataframe}",
                f"- CSV：{record.csv}",
                f"- JSON：{record.json}",
                f"- AI分析引用：{', '.join(record.ai_analysis_refs) if record.ai_analysis_refs else '暂无'}",
                f"- PPT引用页面：{', '.join(record.ppt_refs) if record.ppt_refs else record.page}",
                "",
                "## 追溯链路",
                "",
                f"PPT -> Metric {record.metric_id} -> query.sql -> result.csv/result.json -> 原始数据",
                "",
            ]
        )

    @staticmethod
    def _safe_name(value: str) -> str:
        value = str(value).strip().replace(" ", "_")
        value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
        return value or "metric"
