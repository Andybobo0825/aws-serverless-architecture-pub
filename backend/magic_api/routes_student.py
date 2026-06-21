from __future__ import annotations

from typing import cast

from magic_api.auth import require_active_user, require_student_device
from magic_api.errors import Forbidden
from magic_api.models import ClassId, UserProfile, Week
from magic_api.repositories import Repository


def _validated_class_id(class_id: str) -> ClassId:
    if class_id not in {"jul", "aug"}:
        raise Forbidden("student does not belong to this class")
    return cast(ClassId, class_id)


def require_active_student(profile: UserProfile) -> None:
    require_active_user(profile)
    if profile.role != "student":
        raise Forbidden("requires role student")


def open_week_ids_for_classes(repo: Repository, class_ids: list[ClassId]) -> set[str]:
    opened: set[str] = set()
    for class_id in class_ids:
        opened.update(repo.get_class_access(class_id).open_week_ids)
    return opened


def open_week_ids_for_student(repo: Repository, profile: UserProfile) -> set[str]:
    return open_week_ids_for_classes(repo, profile.classes)


def weeks_visible_for_class(weeks: list[Week], class_id: ClassId) -> list[Week]:
    class_week_numbers = {
        week.week_number for week in weeks if week.class_id == class_id
    }
    return [
        week
        for week in weeks
        if week.class_id == class_id
        or (week.class_id is None and week.week_number not in class_week_numbers)
    ]


def weeks_visible_for_student_classes(repo: Repository, class_ids: list[ClassId]) -> list[Week]:
    all_weeks = repo.list_weeks()
    weeks_by_id: dict[str, Week] = {}
    for class_id in class_ids:
        for week in weeks_visible_for_class(all_weeks, class_id):
            weeks_by_id[week.week_id] = week
    return sorted(
        weeks_by_id.values(),
        key=lambda week: (week.week_number, week.class_id or "", week.week_id),
    )


def list_student_weeks(
    repo: Repository,
    username: str,
    device_id: str | None,
    class_id: str | None = None,
) -> list[dict[str, object]]:
    profile = repo.get_user(username)
    require_active_student(profile)
    require_student_device(profile, device_id, allow_first_registration=False)
    class_ids = profile.classes
    if class_id is not None:
        narrowed_class_id = _validated_class_id(class_id)
        if narrowed_class_id not in profile.classes:
            raise Forbidden("student does not belong to this class")
        class_ids = [narrowed_class_id]
    opened = open_week_ids_for_classes(repo, class_ids)
    weeks = weeks_visible_for_student_classes(repo, class_ids)
    return [
        {
            "week_id": week.week_id,
            "week_number": week.week_number,
            "title": week.title,
            "is_open": week.week_id in opened,
        }
        for week in weeks
    ]


def signed_magic_page_urls(
    magic_pages: list[str],
    magic_page_url_factory=None,
) -> list[dict[str, str]]:
    if magic_page_url_factory is None:
        return []
    return [
        {"name": page, "url": magic_page_url_factory(f"magic-pages/{page}")}
        for page in magic_pages
    ]


def signed_image_cards(
    image_cards: list[dict[str, str]],
    image_url_factory=None,
) -> list[dict[str, str]]:
    return [
        {
            **card,
            **({"url": image_url_factory(card["image_key"])} if image_url_factory else {}),
        }
        for card in image_cards
    ]


def get_student_week_detail(
    repo: Repository,
    username: str,
    week_id: str,
    device_id: str | None,
    pdf_url_factory=None,
    magic_page_url_factory=None,
) -> dict[str, object]:
    profile = repo.get_user(username)
    require_active_student(profile)
    require_student_device(profile, device_id, allow_first_registration=False)
    opened = open_week_ids_for_student(repo, profile)
    if week_id not in opened:
        raise Forbidden("week is not open for this student")
    week = repo.get_week(week_id)
    return {
        "week_id": week.week_id,
        "week_number": week.week_number,
        "title": week.title,
        "pdf_url": pdf_url_factory(week.pdf_s3_key)
        if pdf_url_factory and week.pdf_s3_key
        else None,
        "magic_pages": week.magic_pages,
        "magic_page_urls": signed_magic_page_urls(week.magic_pages, magic_page_url_factory),
        "url_cards": week.url_cards,
        "image_cards": signed_image_cards(week.image_cards, pdf_url_factory),
    }
