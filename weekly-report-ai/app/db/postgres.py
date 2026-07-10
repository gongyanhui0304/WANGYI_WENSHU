"""
PostgreSQL 数据库连接
用于读取 Redmine 数据库的需求数据
"""
import logging
from contextlib import contextmanager
from typing import Optional

import pandas as pd

from app.config import config

logger = logging.getLogger(__name__)


class PostgresClient:
    """PostgreSQL 客户端封装"""

    def __init__(self):
        self._config = config.redmine
        self._available = False

    def test_connection(self) -> dict:
        """测试数据库连接"""
        try:
            import psycopg2
            conn = psycopg2.connect(self._config.connection_string, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            self._available = True
            return {"success": True, "message": "PostgreSQL 连接成功"}
        except ImportError:
            return {"success": False, "message": "psycopg2 未安装，请运行: pip install psycopg2-binary"}
        except Exception as e:
            self._available = False
            return {"success": False, "message": f"PostgreSQL 连接失败: {str(e)}"}

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        import psycopg2
        conn = psycopg2.connect(self._config.connection_string)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        """
        执行 SQL 查询并返回 DataFrame

        Args:
            sql: SQL 查询语句（支持 %(name)s 命名参数）
            params: 参数字典

        Returns:
            pandas DataFrame
        """
        try:
            with self._get_connection() as conn:
                df = pd.read_sql(sql, conn, params=params or {})
                return df
        except Exception as e:
            logger.error(f"PostgreSQL 查询失败: {e}")
            raise

    def execute_query_safe(self, sql: str, params: Optional[dict] = None) -> tuple:
        """
        安全执行查询，返回 (DataFrame, error_message)
        """
        try:
            df = self.execute_query(sql, params)
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    @property
    def is_configured(self) -> bool:
        """检查数据库是否已配置"""
        return bool(self._config.host and self._config.host != "your-postgres-host")


# 全局客户端实例
postgres_client = PostgresClient()
