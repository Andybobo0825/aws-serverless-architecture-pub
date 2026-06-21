from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    users_table: str
    weeks_table: str
    class_access_table: str
    content_bucket: str
    pdf_url_ttl_seconds: int = 300


def load_settings() -> Settings:
    return Settings(
        users_table=os.environ["USERS_TABLE_NAME"],
        weeks_table=os.environ["WEEKS_TABLE_NAME"],
        class_access_table=os.environ["CLASS_ACCESS_TABLE_NAME"],
        content_bucket=os.environ["CONTENT_BUCKET_NAME"],
        pdf_url_ttl_seconds=int(os.environ.get("PDF_URL_TTL_SECONDS", "300")),
    )
