import pytest

from magic_api.errors import BadRequest, Forbidden
from magic_api.routes_common import get_me, register_device, reset_device


def test_get_me_reports_device_binding_state(repo):
    result = get_me(repo, "student-jul")

    assert result == {
        "username": "student-jul",
        "role": "student",
        "status": "active",
        "classes": ["jul"],
        "device_bound": True,
    }


def test_student_can_register_first_device(repo):
    repo.users["student-jul"].device_id = None

    result = register_device(repo, actor_username="student-jul", target_device_id="device-new")

    assert result == {"device_id": "device-new", "status": "registered"}
    assert repo.get_user("student-jul").device_id == "device-new"


def test_student_can_reregister_same_device_idempotently(repo):
    result = register_device(repo, actor_username="student-jul", target_device_id="device-jul")

    assert result == {"device_id": "device-jul", "status": "registered"}
    assert repo.get_user("student-jul").device_id == "device-jul"


def test_student_cannot_overwrite_existing_device(repo):
    with pytest.raises(Forbidden, match="already bound"):
        register_device(repo, actor_username="student-jul", target_device_id="device-new")


def test_device_registration_requires_device_id(repo):
    with pytest.raises(BadRequest, match="device_id is required"):
        register_device(repo, actor_username="student-jul", target_device_id="")


@pytest.mark.parametrize("username", ["teacher01", "admin01"])
def test_non_students_are_not_device_limited(repo, username):
    result = register_device(repo, actor_username=username, target_device_id="any-device")

    assert result == {"device_id": None, "status": "not_required"}
    assert repo.get_user(username).device_id is None


def test_admin_can_reset_student_device(repo):
    result = reset_device(repo, actor_username="admin01", target_username="student-jul")

    assert result == {"username": "student-jul", "device_id": None}
    assert repo.get_user("student-jul").device_id is None


def test_teacher_cannot_reset_student_device(repo):
    with pytest.raises(Forbidden, match="requires role admin"):
        reset_device(repo, actor_username="teacher01", target_username="student-jul")


def test_admin_cannot_reset_non_student_device(repo):
    with pytest.raises(BadRequest, match="only student devices can be reset"):
        reset_device(repo, actor_username="admin01", target_username="teacher01")
