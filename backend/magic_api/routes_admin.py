from __future__ import annotations

from dataclasses import replace
from typing import cast

from magic_api.auth import require_active_user
from magic_api.errors import BadRequest, Forbidden, NotFound
from magic_api.models import ClassAccess, ClassId, Role, UserProfile, UserStatus
from magic_api.repositories import Repository, profile_to_item, week_to_item

VALID_ROLES: set[str] = {"admin", "teacher", "student"}
VALID_STATUSES: set[str] = {"active", "inactive"}
VALID_CLASSES: set[str] = {"jul", "aug"}


def _ensure_weeks_belong_to_class(
    repo: Repository, class_id: ClassId, open_week_ids: list[str]
) -> None:
    known_week_ids = {week.week_id for week in repo.list_weeks()}
    unknown_week_ids = [week_id for week_id in open_week_ids if week_id not in known_week_ids]
    if unknown_week_ids:
        raise BadRequest(f"unknown week ids: {', '.join(unknown_week_ids)}")

    wrong_class_week_ids = [
        week_id
        for week_id in open_week_ids
        if (week := repo.get_week(week_id)).class_id is not None and week.class_id != class_id
    ]
    if wrong_class_week_ids:
        raise BadRequest(
            f"week ids do not belong to class {class_id}: {', '.join(wrong_class_week_ids)}"
        )


def require_admin(repo: Repository, username: str) -> None:
    profile = repo.get_user(username)
    require_active_user(profile)
    if profile.role != "admin":
        raise Forbidden("requires role admin")


def create_or_update_user_profile(
    repo: Repository,
    *,
    actor_username: str,
    username: str,
    role: str,
    status: str,
    classes: list[str],
    temporary_password: str | None = None,
    identity_admin: object | None = None,
    allow_profile_only_without_identity: bool = False,
) -> dict[str, object]:
    require_admin(repo, actor_username)
    if role not in VALID_ROLES:
        raise BadRequest("invalid role")
    if status not in VALID_STATUSES:
        raise BadRequest("invalid status")

    invalid_classes = [class_id for class_id in classes if class_id not in VALID_CLASSES]
    if invalid_classes:
        raise BadRequest(f"invalid classes: {', '.join(invalid_classes)}")

    device_id = None
    try:
        device_id = repo.get_user(username).device_id
    except NotFound:
        pass

    narrowed_role = cast(Role, role)
    narrowed_status = cast(UserStatus, status)
    narrowed_classes: list[ClassId] = [cast(ClassId, class_id) for class_id in classes]
    profile = UserProfile(
        username=username,
        role=narrowed_role,
        status=narrowed_status,
        classes=narrowed_classes,
        device_id=device_id,
    )
    if identity_admin is None:
        if not allow_profile_only_without_identity:
            raise BadRequest("identity admin is not configured")
        repo.save_user(profile)
    else:
        pending_profile = replace(
            profile,
            identity_sync_status="pending",
            identity_sync_error=None,
        )
        repo.save_user(pending_profile)
        try:
            _sync_identity_admin(
                identity_admin,
                username=username,
                role=narrowed_role,
                status=narrowed_status,
                temporary_password=temporary_password,
            )
        except BadRequest as error:
            repo.save_user(
                replace(
                    pending_profile,
                    identity_sync_status="failed",
                    identity_sync_error=error.message,
                )
            )
            raise
        profile = replace(profile, identity_sync_status="synced", identity_sync_error=None)
        repo.save_user(profile)
    return profile_to_item(profile)


def _sync_identity_admin(
    identity_admin: object,
    *,
    username: str,
    role: Role,
    status: UserStatus,
    temporary_password: str | None,
) -> None:
    try:
        identity_admin.upsert_user(
            username=username,
            role=role,
            status=status,
            temporary_password=temporary_password,
        )
    except Exception as error:
        raise BadRequest(str(error)) from error


def sync_user_identity(
    repo: Repository,
    *,
    actor_username: str,
    username: str,
    temporary_password: str | None = None,
    identity_admin: object | None = None,
) -> dict[str, object]:
    """Repair/retry the Cognito side from the DynamoDB profile source of truth."""
    require_admin(repo, actor_username)
    if identity_admin is None:
        raise BadRequest("identity admin is not configured")
    profile = repo.get_user(username)
    repo.save_user(replace(profile, identity_sync_status="pending", identity_sync_error=None))
    try:
        _sync_identity_admin(
            identity_admin,
            username=profile.username,
            role=profile.role,
            status=profile.status,
            temporary_password=temporary_password,
        )
    except BadRequest as error:
        repo.save_user(
            replace(profile, identity_sync_status="failed", identity_sync_error=error.message)
        )
        raise
    repo.save_user(replace(profile, identity_sync_status="synced", identity_sync_error=None))
    return {"username": username, "status": "identity_synced"}


def reset_user_password(
    repo: Repository,
    *,
    actor_username: str,
    username: str,
    temporary_password: str | None,
    identity_admin: object | None = None,
) -> dict[str, object]:
    require_admin(repo, actor_username)
    if not temporary_password:
        raise BadRequest("temporary_password is required")
    repo.get_user(username)
    if identity_admin is None:
        raise BadRequest("identity admin is not configured")
    identity_admin.reset_password(
        username=username,
        temporary_password=temporary_password,
    )
    return {"username": username, "status": "password_reset"}


def list_user_profiles(repo: Repository, *, actor_username: str) -> list[dict[str, object]]:
    require_admin(repo, actor_username)
    return [profile_to_item(profile) for profile in repo.list_users()]


def get_admin_dashboard(repo: Repository, *, actor_username: str) -> dict[str, object]:
    require_admin(repo, actor_username)
    return {
        "users": [profile_to_item(profile) for profile in repo.list_users()],
        "weeks": [week_to_item(week) for week in repo.list_weeks()],
        "class_access": [
            {
                "class_id": class_id,
                "open_week_ids": repo.get_class_access(cast(ClassId, class_id)).open_week_ids,
            }
            for class_id in ("jul", "aug")
        ],
    }


def list_class_open_weeks(
    repo: Repository,
    *,
    actor_username: str,
    class_id: str,
) -> dict[str, object]:
    require_admin(repo, actor_username)
    if class_id not in VALID_CLASSES:
        raise BadRequest("invalid class_id")

    narrowed_class_id = cast(ClassId, class_id)
    access = repo.get_class_access(narrowed_class_id)
    return {"class_id": class_id, "open_week_ids": access.open_week_ids}


def set_class_open_weeks(
    repo: Repository,
    *,
    actor_username: str,
    class_id: str,
    open_week_ids: list[str],
) -> dict[str, object]:
    require_admin(repo, actor_username)
    if class_id not in VALID_CLASSES:
        raise BadRequest("invalid class_id")

    narrowed_class_id = cast(ClassId, class_id)
    _ensure_weeks_belong_to_class(repo, narrowed_class_id, open_week_ids)
    access = ClassAccess(class_id=narrowed_class_id, open_week_ids=open_week_ids)
    repo.save_class_access(access)
    return {"class_id": class_id, "open_week_ids": open_week_ids}


def delete_user_profile(
    repo: Repository,
    *,
    actor_username: str,
    username: str,
    identity_admin: object | None = None,
) -> dict[str, object]:
    require_admin(repo, actor_username)
    if username == actor_username:
        raise BadRequest("cannot delete own account")
    repo.get_user(username)
    if identity_admin is None:
        raise BadRequest("identity admin is not configured")
    try:
        identity_admin.delete_user(username=username)
    except Exception as error:
        raise BadRequest(str(error)) from error
    repo.delete_user(username)
    return {"username": username, "status": "deleted"}
