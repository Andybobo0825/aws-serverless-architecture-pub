from __future__ import annotations

from collections.abc import Mapping

from magic_api.errors import Forbidden, Unauthorized
from magic_api.models import Claims, Role, UserProfile


def claims_from_event(event: Mapping[str, object]) -> Claims:
    try:
        authorizer = event["requestContext"]["authorizer"]  # type: ignore[index]
        jwt = authorizer["jwt"]  # type: ignore[index]
        raw_claims = jwt["claims"]  # type: ignore[index]
    except (KeyError, TypeError):
        raise Unauthorized("missing JWT claims") from None
    if not isinstance(raw_claims, Mapping):
        raise Unauthorized("missing JWT claims")

    username = raw_claims.get("cognito:username") or raw_claims.get("username")
    if not isinstance(username, str) or not username:
        raise Unauthorized("missing username claim")

    raw_groups = raw_claims.get("cognito:groups", [])
    if isinstance(raw_groups, str):
        groups = tuple(group.strip() for group in raw_groups.split(",") if group.strip())
    elif isinstance(raw_groups, list):
        groups = tuple(str(group) for group in raw_groups)
    else:
        groups = ()
    return Claims(username=username, groups=groups)


def require_role(claims: Claims, role: Role) -> None:
    if role not in claims.groups:
        raise Forbidden(f"requires role {role}")


def has_any_role(claims: Claims, roles: set[Role]) -> bool:
    return bool(set(claims.groups).intersection(roles))


def require_any_role(claims: Claims, roles: set[Role]) -> None:
    if not has_any_role(claims, roles):
        joined = ", ".join(sorted(roles))
        raise Forbidden(f"requires one of roles {joined}")


def require_active_user(profile: UserProfile) -> None:
    if profile.status != "active":
        raise Forbidden("user is inactive")
    if profile.identity_sync_status != "synced":
        raise Forbidden("identity sync is not complete")


def require_student_device(
    profile: UserProfile,
    device_id: str | None,
    *,
    allow_first_registration: bool,
) -> None:
    if profile.role != "student":
        return
    if not device_id:
        raise Forbidden("student device id is required")
    if profile.device_id is None and allow_first_registration:
        return
    if profile.device_id != device_id:
        raise Forbidden("student device is not authorized")
