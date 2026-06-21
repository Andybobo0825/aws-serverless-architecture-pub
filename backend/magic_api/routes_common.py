from __future__ import annotations

from magic_api.auth import require_active_user
from magic_api.errors import BadRequest, Forbidden
from magic_api.repositories import Repository


def get_me(repo: Repository, username: str) -> dict[str, object]:
    profile = repo.get_user(username)
    require_active_user(profile)
    return {
        "username": profile.username,
        "role": profile.role,
        "status": profile.status,
        "classes": profile.classes,
        "device_bound": profile.device_id is not None,
    }


def register_device(
    repo: Repository,
    *,
    actor_username: str,
    target_device_id: str,
) -> dict[str, object]:
    if not target_device_id:
        raise BadRequest("device_id is required")
    profile = repo.get_user(actor_username)
    require_active_user(profile)
    if profile.role != "student":
        return {"device_id": None, "status": "not_required"}
    if profile.device_id is not None and profile.device_id != target_device_id:
        raise Forbidden("student device is already bound")
    profile.device_id = target_device_id
    repo.save_user(profile)
    return {"device_id": target_device_id, "status": "registered"}


def reset_device(
    repo: Repository, *, actor_username: str, target_username: str
) -> dict[str, object]:
    actor = repo.get_user(actor_username)
    require_active_user(actor)
    if actor.role != "admin":
        raise Forbidden("requires role admin")
    target = repo.get_user(target_username)
    if target.role != "student":
        raise BadRequest("only student devices can be reset")
    target.device_id = None
    repo.save_user(target)
    return {"username": target.username, "device_id": None}
