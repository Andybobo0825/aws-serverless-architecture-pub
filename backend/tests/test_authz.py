import pytest

from magic_api.auth import (
    claims_from_event,
    require_active_user,
    require_role,
    require_student_device,
)
from magic_api.errors import Forbidden, Unauthorized
from magic_api.models import Claims, UserProfile


def _http_api_event(claims):
    return {"requestContext": {"authorizer": {"jwt": {"claims": claims}}}}


def test_claims_from_event_accepts_http_api_cognito_username():
    claims = claims_from_event(_http_api_event({"cognito:username": "teacher01"}))

    assert claims == Claims(username="teacher01", groups=())


def test_claims_from_event_falls_back_to_username_claim():
    claims = claims_from_event(_http_api_event({"username": "student001"}))

    assert claims == Claims(username="student001", groups=())


def test_claims_from_event_parses_comma_separated_cognito_groups():
    claims = claims_from_event(
        _http_api_event(
            {"cognito:username": "teacher01", "cognito:groups": "teacher, admin"}
        )
    )

    assert claims == Claims(username="teacher01", groups=("teacher", "admin"))


def test_claims_from_event_parses_list_cognito_groups():
    claims = claims_from_event(
        _http_api_event({"cognito:username": "teacher01", "cognito:groups": ["teacher", "admin"]})
    )

    assert claims == Claims(username="teacher01", groups=("teacher", "admin"))


def test_claims_from_event_rejects_missing_claims():
    with pytest.raises(Unauthorized, match="missing JWT claims"):
        claims_from_event({"requestContext": {"authorizer": {"jwt": {}}}})


def test_claims_from_event_rejects_non_mapping_claims_without_attribute_error():
    with pytest.raises(Unauthorized, match="missing JWT claims"):
        claims_from_event(_http_api_event([("cognito:username", "teacher01")]))


def test_require_role_allows_matching_group():
    claims = Claims(username="teacher01", groups=("teacher",))
    require_role(claims, "teacher")


def test_require_role_rejects_missing_group():
    claims = Claims(username="student001", groups=("student",))
    with pytest.raises(Forbidden, match="requires role teacher"):
        require_role(claims, "teacher")


def test_require_active_user_rejects_inactive_profile():
    profile = UserProfile(username="student001", role="student", status="inactive")
    with pytest.raises(Forbidden, match="inactive"):
        require_active_user(profile)


@pytest.mark.parametrize("sync_status", ["pending", "failed"])
def test_require_active_user_rejects_unsynced_identity_profile(sync_status):
    profile = UserProfile(
        username="student001",
        role="student",
        identity_sync_status=sync_status,
    )
    with pytest.raises(Forbidden, match="identity sync is not complete"):
        require_active_user(profile)


def test_require_student_device_allows_first_registration():
    profile = UserProfile(username="student001", role="student", device_id=None)
    require_student_device(profile, "device-a", allow_first_registration=True)


def test_require_student_device_rejects_different_device():
    profile = UserProfile(username="student001", role="student", device_id="device-a")
    with pytest.raises(Forbidden, match="device"):
        require_student_device(profile, "device-b", allow_first_registration=False)


def test_require_student_device_ignores_teacher():
    profile = UserProfile(username="teacher01", role="teacher", device_id=None)
    require_student_device(profile, "any-device", allow_first_registration=False)
