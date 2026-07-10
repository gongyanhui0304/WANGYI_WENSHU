"""
应用配置模块
从 .env 文件加载配置，支持环境变量覆盖
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 加载 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


class SmartBIConfig(BaseModel):
    """SmartBI SQL Server 数据库配置"""
    host: str = Field(default_factory=lambda: os.getenv("SMARTBI_SQLSERVER_HOST", ""))
    port: int = Field(default_factory=lambda: int(os.getenv("SMARTBI_SQLSERVER_PORT", "1433")))
    database: str = Field(default_factory=lambda: os.getenv("SMARTBI_SQLSERVER_DATABASE", "SmartBI"))
    user: str = Field(default_factory=lambda: os.getenv("SMARTBI_SQLSERVER_USER", ""))
    password: str = Field(default_factory=lambda: os.getenv("SMARTBI_SQLSERVER_PASSWORD", ""))
    driver: str = Field(default_factory=lambda: os.getenv("SMARTBI_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"))

    @property
    def connection_string(self) -> str:
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
        )


class RedmineConfig(BaseModel):
    """Redmine PostgreSQL 数据库配置"""
    host: str = Field(default_factory=lambda: os.getenv("REDMINE_POSTGRES_HOST", ""))
    port: int = Field(default_factory=lambda: int(os.getenv("REDMINE_POSTGRES_PORT", "5432")))
    database: str = Field(default_factory=lambda: os.getenv("REDMINE_POSTGRES_DATABASE", "redmine"))
    user: str = Field(default_factory=lambda: os.getenv("REDMINE_POSTGRES_USER", ""))
    password: str = Field(default_factory=lambda: os.getenv("REDMINE_POSTGRES_PASSWORD", ""))

    @property
    def connection_string(self) -> str:
        return (
            f"host={self.host} port={self.port} "
            f"dbname={self.database} user={self.user} password={self.password}"
        )


class DeepSeekConfig(BaseModel):
    """DeepSeek AI API 配置"""
    api_key: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
    model: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))


class AppConfig(BaseModel):
    """应用全局配置"""
    name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "信息中心周报智能生成系统"))
    env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    debug: bool = Field(default_factory=lambda: os.getenv("APP_DEBUG", "true").lower() == "true")
    secret_key: str = Field(default_factory=lambda: os.getenv("APP_SECRET_KEY", "dev-secret-key"))

    # 本地数据库
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            f"sqlite:///{BASE_DIR / 'data' / 'sqlite' / 'weekly_report.db'}"
        )
    )

    # 子配置
    smartbi: SmartBIConfig = SmartBIConfig()
    redmine: RedmineConfig = RedmineConfig()
    deepseek: DeepSeekConfig = DeepSeekConfig()

    # 文件路径
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    export_dir: Path = BASE_DIR / "data" / "exports"
    sqlite_dir: Path = BASE_DIR / "data" / "sqlite"

    # 知识库（SQL模板 & 指标字典）
    knowledge_dir: Path = BASE_DIR / "knowledge"
    smartbi_sql_dir: Path = BASE_DIR / "knowledge" / "smartbi" / "sql"
    redmine_sql_dir: Path = BASE_DIR / "knowledge" / "redmine" / "sql"

    # 兼容旧版（废弃）
    sql_template_dir: Path = BASE_DIR / "app" / "sql_templates"

    max_pdf_size_mb: int = int(os.getenv("WEEKLY_REPORT_MAX_PDF_SIZE_MB", "20"))


# 全局配置实例
config = AppConfig()

# 确保数据目录存在
config.upload_dir.mkdir(parents=True, exist_ok=True)
config.export_dir.mkdir(parents=True, exist_ok=True)
config.sqlite_dir.mkdir(parents=True, exist_ok=True)
config.smartbi_sql_dir.mkdir(parents=True, exist_ok=True)
config.redmine_sql_dir.mkdir(parents=True, exist_ok=True)
