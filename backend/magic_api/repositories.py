from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any, Protocol, cast

from magic_api.errors import BadRequest, NotFound
from magic_api.models import (
    ClassAccess,
    ClassId,
    IdentitySyncStatus,
    ImageCard,
    Role,
    UrlCard,
    UserProfile,
    UserStatus,
    Week,
)


class Repository(Protocol):
    def get_user(self, username: str) -> UserProfile: ...
    def save_user(self, profile: UserProfile) -> None: ...
    def delete_user(self, username: str) -> None: ...
    def list_users(self) -> list[UserProfile]: ...
    def get_week(self, week_id: str) -> Week: ...
    def list_weeks(self) -> list[Week]: ...
    def save_week(self, week: Week) -> None: ...
    def delete_week(self, week_id: str) -> None: ...
    def get_class_access(self, class_id: ClassId) -> ClassAccess: ...
    def save_class_access(self, access: ClassAccess) -> None: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self.users: dict[str, UserProfile] = {}
        self.weeks: dict[str, Week] = {}
        self.class_access: dict[str, ClassAccess] = {}

    def get_user(self, username: str) -> UserProfile:
        try:
            return self.users[username]
        except KeyError:
            raise NotFound(f"user {username} not found") from None

    def save_user(self, profile: UserProfile) -> None:
        self.users[profile.username] = profile

    def delete_user(self, username: str) -> None:
        try:
            del self.users[username]
        except KeyError:
            raise NotFound(f"user {username} not found") from None

    def list_users(self) -> list[UserProfile]:
        return sorted(self.users.values(), key=lambda user: user.username)

    def get_week(self, week_id: str) -> Week:
        try:
            return self.weeks[week_id]
        except KeyError:
            raise NotFound(f"week {week_id} not found") from None

    def list_weeks(self) -> list[Week]:
        return sorted(
            self.weeks.values(),
            key=lambda week: (week.class_id or "", week.week_number, week.week_id),
        )

    def save_week(self, week: Week) -> None:
        self.weeks[week.week_id] = week

    def delete_week(self, week_id: str) -> None:
        try:
            del self.weeks[week_id]
        except KeyError:
            raise NotFound(f"week {week_id} not found") from None

    def get_class_access(self, class_id: ClassId) -> ClassAccess:
        return self.class_access.get(class_id, ClassAccess(class_id=class_id, open_week_ids=[]))

    def save_class_access(self, access: ClassAccess) -> None:
        self.class_access[access.class_id] = access


def profile_to_item(profile: UserProfile) -> dict[str, object]:
    return asdict(profile)


def week_to_item(week: Week) -> dict[str, object]:
    return asdict(week)


VALID_CLASS_IDS = {"jul", "aug"}
VALID_ROLES = {"admin", "teacher", "student"}
VALID_STATUSES = {"active", "inactive"}
VALID_IDENTITY_SYNC_STATUSES = {"pending", "synced", "failed"}


def _string_field(item: Mapping[str, Any], field: str) -> str:
    value = item.get(field)
    if not isinstance(value, str):
        raise BadRequest(f"invalid {field}")
    return value


def _optional_string_field(item: Mapping[str, Any], field: str) -> str | None:
    value = item.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise BadRequest(f"invalid {field}")
    return value


def _string_list_field(item: Mapping[str, Any], field: str) -> list[str]:
    value = item.get(field, [])
    if not isinstance(value, list) or not all(isinstance(element, str) for element in value):
        raise BadRequest(f"invalid {field}")
    return list(value)


def _url_cards_field(item: Mapping[str, Any]) -> list[UrlCard]:
    value = item.get("url_cards", [])
    if not isinstance(value, list):
        raise BadRequest("invalid url_cards")
    cards: list[UrlCard] = []
    for card in value:
        if not isinstance(card, Mapping):
            raise BadRequest("invalid url_cards")
        name = card.get("name")
        url = card.get("url")
        if not isinstance(name, str) or not isinstance(url, str):
            raise BadRequest("invalid url_cards")
        cards.append({"name": name, "url": url})
    return cards


def _image_cards_field(item: Mapping[str, Any]) -> list[ImageCard]:
    value = item.get("image_cards", [])
    if not isinstance(value, list):
        raise BadRequest("invalid image_cards")
    cards: list[ImageCard] = []
    for card in value:
        if not isinstance(card, Mapping):
            raise BadRequest("invalid image_cards")
        name = card.get("name")
        image_key = card.get("image_key")
        content_type = card.get("content_type")
        if (
            not isinstance(name, str)
            or not isinstance(image_key, str)
            or not isinstance(content_type, str)
        ):
            raise BadRequest("invalid image_cards")
        cards.append({"name": name, "image_key": image_key, "content_type": content_type})
    return cards


def _class_id(value: str) -> ClassId:
    if value not in VALID_CLASS_IDS:
        raise BadRequest("invalid class_id")
    return cast(ClassId, value)


def _class_ids(values: list[str]) -> list[ClassId]:
    return [_class_id(value) for value in values]


def _user_profile_from_item(item: Mapping[str, Any]) -> UserProfile:
    role = _string_field(item, "role")
    if role not in VALID_ROLES:
        raise BadRequest("invalid role")
    status = item.get("status", "active")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        raise BadRequest("invalid status")
    identity_sync_status = item.get("identity_sync_status", "synced")
    if (
        not isinstance(identity_sync_status, str)
        or identity_sync_status not in VALID_IDENTITY_SYNC_STATUSES
    ):
        raise BadRequest("invalid identity_sync_status")
    return UserProfile(
        username=_string_field(item, "username"),
        role=cast(Role, role),
        status=cast(UserStatus, status),
        classes=_class_ids(_string_list_field(item, "classes")),
        device_id=_optional_string_field(item, "device_id"),
        identity_sync_status=cast(IdentitySyncStatus, identity_sync_status),
        identity_sync_error=_optional_string_field(item, "identity_sync_error"),
    )


def _week_from_item(item: Mapping[str, Any]) -> Week:
    raw_class_id = _optional_string_field(item, "class_id")
    class_id = _class_id(raw_class_id) if raw_class_id is not None else None
    return Week(
        week_id=_string_field(item, "week_id"),
        week_number=int(item.get("week_number", 0)),
        title=_string_field(item, "title"),
        pdf_s3_key=_optional_string_field(item, "pdf_s3_key"),
        magic_pages=_string_list_field(item, "magic_pages"),
        url_cards=_url_cards_field(item),
        image_cards=_image_cards_field(item),
        class_id=class_id,
        created_by=str(item.get("created_by", "system")),
    )


def _scan_all_items(table: Any, scan_name: str) -> list[Mapping[str, Any]]:
    # MVP scans are acceptable while tables stay tiny (~50 users and a small week count).
    # Future scale should add DynamoDB indexes plus API-level pagination.
    items: list[Mapping[str, Any]] = []
    scan_kwargs: dict[str, Any] = {}
    while True:
        response = table.scan(**scan_kwargs)
        page_items = response.get("Items", [])
        if not isinstance(page_items, list):
            raise BadRequest(f"invalid {scan_name} scan")
        for item in page_items:
            if not isinstance(item, Mapping):
                raise BadRequest(f"invalid {scan_name} scan item")
            items.append(item)
        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            return items
        if not isinstance(last_evaluated_key, Mapping):
            raise BadRequest(f"invalid {scan_name} scan pagination key")
        scan_kwargs = {"ExclusiveStartKey": dict(last_evaluated_key)}


class DynamoDbRepository:
    def __init__(
        self,
        dynamodb_resource: Any,
        *,
        users_table: str,
        weeks_table: str,
        class_access_table: str,
    ) -> None:
        self.users_table = dynamodb_resource.Table(users_table)
        self.weeks_table = dynamodb_resource.Table(weeks_table)
        self.class_access_table = dynamodb_resource.Table(class_access_table)

    def get_user(self, username: str) -> UserProfile:
        response = self.users_table.get_item(Key={"username": username})
        item = response.get("Item")
        if not isinstance(item, Mapping):
            raise NotFound(f"user {username} not found")
        return _user_profile_from_item(item)

    def save_user(self, profile: UserProfile) -> None:
        self.users_table.put_item(Item=profile_to_item(profile))

    def delete_user(self, username: str) -> None:
        self.get_user(username)
        self.users_table.delete_item(Key={"username": username})

    def list_users(self) -> list[UserProfile]:
        return sorted(
            [_user_profile_from_item(item) for item in _scan_all_items(self.users_table, "users")],
            key=lambda user: user.username,
        )

    def get_week(self, week_id: str) -> Week:
        response = self.weeks_table.get_item(Key={"week_id": week_id})
        item = response.get("Item")
        if not isinstance(item, Mapping):
            raise NotFound(f"week {week_id} not found")
        return _week_from_item(item)

    def list_weeks(self) -> list[Week]:
        weeks = [_week_from_item(item) for item in _scan_all_items(self.weeks_table, "weeks")]
        return sorted(weeks, key=lambda week: week.week_number)

    def save_week(self, week: Week) -> None:
        self.weeks_table.put_item(Item=week_to_item(week))

    def delete_week(self, week_id: str) -> None:
        self.get_week(week_id)
        self.weeks_table.delete_item(Key={"week_id": week_id})

    def get_class_access(self, class_id: ClassId) -> ClassAccess:
        response = self.class_access_table.get_item(Key={"class_id": class_id})
        item = response.get("Item")
        if not isinstance(item, Mapping):
            return ClassAccess(class_id=class_id, open_week_ids=[])
        return ClassAccess(
            class_id=_class_id(_string_field(item, "class_id")),
            open_week_ids=_string_list_field(item, "open_week_ids"),
        )

    def save_class_access(self, access: ClassAccess) -> None:
        self.class_access_table.put_item(
            Item={"class_id": access.class_id, "open_week_ids": access.open_week_ids}
        )
