import os
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class BaseConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
        case_sensitive=False,
    )


class ArxivSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="ARXIV__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    base_url: str = "https://export.arxiv.org/api/query"
    pdf_cache_dir: str = "./data/arxiv_pdfs"
    rate_limit_delay: float = 3.0
    timeout_seconds: int = 60
    max_results: int = 15
    search_category: str = "cs.AI"
    download_max_retries: int = 3
    download_retry_delay_base: float = 5.0
    max_concurrent_downloads: int = 5
    max_concurrent_parsing: int = 1

    namespaces: dict = {
        "atom": "http://www.w3.org/2005/Atom",
        "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    @field_validator("pdf_cache_dir")
    @classmethod
    def validate_cache_dir(cls, v: str) -> str:
        os.makedirs(v, exist_ok=True)
        return v
    
class ChunkingSettings(BaseConfigSettings):
    model_config=SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="CHUNKING__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )
    chunk_size: int = 600
    overlap_size : int = 100
    min_chunk_size : int = 100
    section_based: bool = True  # Use section-based chunking when available
    



class PDFParserSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="PDF_PARSER__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    max_pages: int = 30
    max_file_size_mb: int = 20
    do_ocr: bool = False
    do_table_structure: bool = True

class Settings(BaseConfigSettings):

    app_version: str = "0.1.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"
    service_name: str = "rag-api"

    postgres_database_url: str = Field(
        default="postgresql://rag_user:rag_password@localhost:5432/rag_db",
        validation_alias="POSTGRES_DATABASE_URL"
    )

    postgres_echo_sql: bool = False
    postgres_pool_size: int = 5
    postgres_max_overflow: int = 0

    arxiv: ArxivSettings = Field(default_factory=ArxivSettings)
    pdf_parser: PDFParserSettings = Field(default_factory=PDFParserSettings)
    chunker : ChunkingSettings = Field(default_factory=ChunkingSettings)



def get_settings() -> Settings:
    return Settings()