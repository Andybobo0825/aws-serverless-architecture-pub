from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict

Role = Literal["admin", "teacher", "student"]
UserStatus = Literal["active", "inactive"]
IdentitySyncStatus = Literal["pending", "synced", "failed"]
ClassId = Literal["jul", "aug"]


class UrlCard(TypedDict):
    name: str
    url: str


class ImageCard(TypedDict):
    name: str
    image_key: str
    content_type: str


@dataclass(frozen=True)
class Claims:
    username: str
    groups: tuple[str, ...]


@dataclass
class UserProfile:
    username: str
    role: Role
    status: UserStatus = "active"
    classes: list[ClassId] = field(default_factory=list)
    device_id: str | None = None
    identity_sync_status: IdentitySyncStatus = "synced"
    identity_sync_error: str | None = None


@dataclass
class Week:
    week_id: str
    week_number: int
    title: str
    pdf_s3_key: str | None = None
    magic_pages: list[str] = field(default_factory=list)
    url_cards: list[UrlCard] = field(default_factory=list)
    image_cards: list[ImageCard] = field(default_factory=list)
    class_id: ClassId | None = None
    created_by: str = "system"


@dataclass
class ClassAccess:
    class_id: ClassId
    open_week_ids: list[str] = field(default_factory=list)
