from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any, cast
from urllib.parse import urlparse
from uuid import uuid4

from magic_api.auth import require_active_user
from magic_api.errors import BadRequest, Forbidden
from magic_api.models import ClassAccess, ClassId, ImageCard, UrlCard, Week
from magic_api.repositories import Repository, week_to_item
from magic_api.routes_student import signed_image_cards, signed_magic_page_urls

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _pdf_title_from_key(key: str) -> str:
    filename = key.rsplit("/", 1)[-1]
    return filename[:-4] if filename.lower().endswith(".pdf") else filename


def _is_safe_magic_page_name(page: str) -> bool:
    return (
        bool(page)
        and page.lower().endswith(".html")
        and not page.startswith("/")
        and ".." not in page
    )


def _is_safe_external_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _validated_url_cards(url_cards: list[Any]) -> list[UrlCard]:
    validated: list[UrlCard] = []
    for raw_card in url_cards:
        if not isinstance(raw_card, Mapping):
            raise BadRequest("invalid url cards")
        raw_name = raw_card.get("name")
        raw_url = raw_card.get("url")
        if not isinstance(raw_name, str) or not isinstance(raw_url, str):
            raise BadRequest("invalid url cards")
        name = raw_name.strip()
        url = raw_url.strip()
        if not name or not _is_safe_external_url(url):
            raise BadRequest("invalid url cards")
        validated.append({"name": name, "url": url})
    return validated


def _safe_image_filename(filename: str, content_type: str) -> str:
    extension = SUPPORTED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise BadRequest("unsupported image type")
    raw_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    stem = raw_name.rsplit(".", 1)[0] if "." in raw_name else raw_name
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", stem).strip("-._")
    if not slug:
        slug = "image"
    return f"{slug}{extension}"


def _is_valid_image_key(image_key: str, content_type: str) -> bool:
    extension = SUPPORTED_IMAGE_TYPES.get(content_type)
    return (
        extension is not None
        and image_key.startswith("images/")
        and ".." not in image_key
        and image_key.lower().endswith(extension)
    )


def _validated_image_cards(image_cards: list[Any]) -> list[ImageCard]:
    validated: list[ImageCard] = []
    for raw_card in image_cards:
        if not isinstance(raw_card, Mapping):
            raise BadRequest("invalid image cards")
        raw_name = raw_card.get("name")
        raw_image_key = raw_card.get("image_key")
        raw_content_type = raw_card.get("content_type")
        if (
            not isinstance(raw_name, str)
            or not isinstance(raw_image_key, str)
            or not isinstance(raw_content_type, str)
        ):
            raise BadRequest("invalid image cards")
        name = raw_name.strip()
        image_key = raw_image_key.strip()
        content_type = raw_content_type.strip().lower()
        if not name or not _is_valid_image_key(image_key, content_type):
            raise BadRequest("invalid image cards")
        validated.append({"name": name, "image_key": image_key, "content_type": content_type})
    return validated


def _validated_class_id(class_id: str) -> ClassId:
    if class_id not in {"jul", "aug"}:
        raise BadRequest("invalid class_id")
    return cast(ClassId, class_id)


def _week_id_for(class_id: ClassId | None, week_number: int) -> str:
    base = f"week-{week_number:03d}"
    return f"{class_id}-{base}" if class_id else base


def _ensure_known_weeks(repo: Repository, open_week_ids: list[str]) -> None:
    known_week_ids = {week.week_id for week in repo.list_weeks()}
    unknown_week_ids = [week_id for week_id in open_week_ids if week_id not in known_week_ids]
    if unknown_week_ids:
        raise BadRequest(f"unknown week ids: {', '.join(unknown_week_ids)}")


def _ensure_weeks_belong_to_class(
    repo: Repository, class_id: ClassId, open_week_ids: list[str]
) -> None:
    _ensure_known_weeks(repo, open_week_ids)
    wrong_class_week_ids = [
        week_id
        for week_id in open_week_ids
        if (week := repo.get_week(week_id)).class_id is not None and week.class_id != class_id
    ]
    if wrong_class_week_ids:
        raise BadRequest(
            f"week ids do not belong to class {class_id}: {', '.join(wrong_class_week_ids)}"
        )


def require_teacher_or_admin(repo: Repository, username: str) -> None:
    profile = repo.get_user(username)
    require_active_user(profile)
    if profile.role not in {"teacher", "admin"}:
        raise Forbidden("requires teacher or admin")


def create_week(
    repo: Repository,
    *,
    actor_username: str,
    week_number: int,
    title: str,
    class_id: str | None = None,
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    if week_number < 1:
        raise BadRequest("week_number must be positive")
    narrowed_class_id = _validated_class_id(class_id) if class_id is not None else None
    week = Week(
        week_id=_week_id_for(narrowed_class_id, week_number),
        week_number=week_number,
        title=title,
        class_id=narrowed_class_id,
        created_by=actor_username,
    )
    repo.save_week(week)
    return week_to_item(week)


def delete_week(repo: Repository, *, actor_username: str, week_id: str) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    repo.get_week(week_id)
    repo.delete_week(week_id)
    for class_id in ("jul", "aug"):
        narrowed_class_id = cast(ClassId, class_id)
        access = repo.get_class_access(narrowed_class_id)
        filtered_week_ids = [
            open_week_id for open_week_id in access.open_week_ids if open_week_id != week_id
        ]
        if filtered_week_ids != access.open_week_ids:
            repo.save_class_access(
                ClassAccess(class_id=narrowed_class_id, open_week_ids=filtered_week_ids)
            )
    return {"week_id": week_id, "status": "deleted"}


def list_teacher_weeks(
    repo: Repository, *, actor_username: str, class_id: str | None = None
) -> list[dict[str, object]]:
    require_teacher_or_admin(repo, actor_username)
    narrowed_class_id = _validated_class_id(class_id) if class_id is not None else None
    weeks = _weeks_visible_for_class(repo.list_weeks(), narrowed_class_id)
    return [week_to_item(week) for week in weeks]


def _weeks_visible_for_class(weeks: list[Week], class_id: ClassId | None) -> list[Week]:
    if class_id is None:
        return weeks
    class_week_numbers = {
        week.week_number for week in weeks if week.class_id == class_id
    }
    return [
        week
        for week in weeks
        if week.class_id == class_id
        or (week.class_id is None and week.week_number not in class_week_numbers)
    ]


def _content_assets_from_keys(
    object_keys: list[str],
    *,
    pdf_url_factory: Callable[[str], str] | None = None,
    magic_page_url_factory: Callable[[str], str] | None = None,
) -> dict[str, object]:
    pdfs = [
        {
            "key": key,
            "name": key.rsplit("/", 1)[-1],
            "title": _pdf_title_from_key(key),
            **({"pdf_url": pdf_url_factory(key)} if pdf_url_factory else {}),
        }
        for key in object_keys
        if key.startswith("pdf/") and key.lower().endswith(".pdf")
    ]
    magic_pages = [
        {
            "key": key,
            "name": key.removeprefix("magic-pages/"),
            **({"url": magic_page_url_factory(key)} if magic_page_url_factory else {}),
        }
        for key in object_keys
        if key.startswith("magic-pages/")
        and _is_safe_magic_page_name(key.removeprefix("magic-pages/"))
    ]
    return {
        "pdfs": sorted(pdfs, key=lambda item: item["name"]),
        "magic_pages": sorted(magic_pages, key=lambda item: item["name"]),
    }


def update_week_content(
    repo: Repository,
    *,
    actor_username: str,
    week_id: str,
    title: str | None,
    pdf_s3_key: str | None,
    magic_pages: list[str] | None,
    url_cards: list[Any] | None = None,
    image_cards: list[Any] | None = None,
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    week = repo.get_week(week_id)
    if title is not None:
        week.title = title
    if pdf_s3_key is not None:
        if not pdf_s3_key.startswith("pdf/") or not pdf_s3_key.lower().endswith(".pdf"):
            raise BadRequest("pdf_s3_key must be a PDF under pdf/")
        week.pdf_s3_key = pdf_s3_key
    if magic_pages is not None:
        invalid_pages = [page for page in magic_pages if not _is_safe_magic_page_name(page)]
        if invalid_pages:
            raise BadRequest(f"invalid magic pages: {', '.join(invalid_pages)}")
        week.magic_pages = magic_pages
    if url_cards is not None:
        week.url_cards = _validated_url_cards(url_cards)
    if image_cards is not None:
        week.image_cards = _validated_image_cards(image_cards)
    repo.save_week(week)
    return week_to_item(week)


def create_week_image_upload(
    repo: Repository,
    *,
    actor_username: str,
    week_id: str,
    filename: str,
    content_type: str,
    upload_url_factory: Callable[[str, str], str] | None,
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    repo.get_week(week_id)
    normalized_content_type = content_type.strip().lower()
    safe_filename = _safe_image_filename(filename, normalized_content_type)
    if upload_url_factory is None:
        raise BadRequest("image upload is not configured")
    image_key = f"images/{week_id}/{uuid4().hex}-{safe_filename}"
    return {
        "image_key": image_key,
        "content_type": normalized_content_type,
        "upload_url": upload_url_factory(image_key, normalized_content_type),
    }


def list_teacher_class_open_weeks(
    repo: Repository,
    *,
    actor_username: str,
    class_id: str,
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    narrowed_class_id = _validated_class_id(class_id)
    access = repo.get_class_access(narrowed_class_id)
    return {"class_id": class_id, "open_week_ids": access.open_week_ids}


def set_teacher_class_open_weeks(
    repo: Repository,
    *,
    actor_username: str,
    class_id: str,
    open_week_ids: list[str],
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    narrowed_class_id = _validated_class_id(class_id)
    _ensure_weeks_belong_to_class(repo, narrowed_class_id, open_week_ids)
    access = ClassAccess(class_id=narrowed_class_id, open_week_ids=open_week_ids)
    repo.save_class_access(access)
    return {"class_id": class_id, "open_week_ids": open_week_ids}


def get_teacher_week_detail(
    repo: Repository,
    *,
    actor_username: str,
    week_id: str,
    pdf_url_factory=None,
    pdf_upload_url_factory=None,
    magic_page_url_factory=None,
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    week = repo.get_week(week_id)
    item = week_to_item(week)
    item["pdf_url"] = (
        pdf_url_factory(week.pdf_s3_key) if pdf_url_factory and week.pdf_s3_key else None
    )
    item["pdf_upload_url"] = (
        pdf_upload_url_factory(f"pdf/{week.week_id}.pdf") if pdf_upload_url_factory else None
    )
    item["magic_page_urls"] = signed_magic_page_urls(week.magic_pages, magic_page_url_factory)
    item["image_cards"] = signed_image_cards(week.image_cards, pdf_url_factory)
    return item


def list_content_assets(
    repo: Repository,
    *,
    actor_username: str,
    object_keys: list[str],
    pdf_url_factory: Callable[[str], str] | None = None,
    magic_page_url_factory: Callable[[str], str] | None = None,
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    return _content_assets_from_keys(
        object_keys,
        pdf_url_factory=pdf_url_factory,
        magic_page_url_factory=magic_page_url_factory,
    )


def get_teacher_dashboard(
    repo: Repository,
    *,
    actor_username: str,
    object_keys: list[str],
    pdf_url_factory: Callable[[str], str] | None = None,
    magic_page_url_factory: Callable[[str], str] | None = None,
) -> dict[str, object]:
    require_teacher_or_admin(repo, actor_username)
    all_weeks = repo.list_weeks()
    return {
        "class_access": [
            {"class_id": class_id, "open_week_ids": repo.get_class_access(class_id).open_week_ids}
            for class_id in ("jul", "aug")
        ],
        "class_weeks": {
            class_id: [
                week_to_item(week)
                for week in _weeks_visible_for_class(all_weeks, class_id)
            ]
            for class_id in ("jul", "aug")
        },
        "assets": _content_assets_from_keys(
            object_keys=object_keys,
            pdf_url_factory=pdf_url_factory,
            magic_page_url_factory=magic_page_url_factory,
        ),
    }
