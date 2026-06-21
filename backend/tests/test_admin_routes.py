import json

import pytest

from magic_api.errors import BadRequest, Forbidden, NotFound
from magic_api.models import UserProfile, Week
from magic_api.routes_admin import (
    create_or_update_user_profile,
    get_admin_dashboard,
    list_class_open_weeks,
    list_user_profiles,
    set_class_open_weeks,
    sync_user_identity,
)


def test_admin_can_create_student_profile(repo):
    result = create_or_update_user_profile(
        repo,
        actor_username="admin01",
        username="student-new",
        role="student",
        status="active",
        classes=["jul", "aug"],
        allow_profile_only_without_identity=True,
    )

    assert result["username"] == "student-new"
    assert result["role"] == "student"
    assert result["status"] == "active"
    assert result["classes"] == ["jul", "aug"]
    assert repo.get_user("student-new").classes == ["jul", "aug"]


def test_admin_profile_creation_requires_identity_admin_by_default(repo):
    with pytest.raises(BadRequest, match="identity admin is not configured"):
        create_or_update_user_profile(
            repo,
            actor_username="admin01",
            username="student-new",
            role="student",
            status="active",
            classes=["jul"],
        )

    with pytest.raises(NotFound):
        repo.get_user("student-new")


def test_admin_can_list_user_profiles(repo):
    result = list_user_profiles(repo, actor_username="admin01")

    assert [user["username"] for user in result] == [
        "admin01",
        "student-aug",
        "student-both",
        "student-jul",
        "teacher01",
    ]


def test_admin_dashboard_combines_users_weeks_and_class_access(repo):
    result = get_admin_dashboard(repo, actor_username="admin01")

    assert [user["username"] for user in result["users"]] == [
        "admin01",
        "student-aug",
        "student-both",
        "student-jul",
        "teacher01",
    ]
    assert [week["week_id"] for week in result["weeks"]] == ["week-001", "week-002", "week-003"]
    assert result["class_access"] == [
        {"class_id": "jul", "open_week_ids": ["week-001"]},
        {"class_id": "aug", "open_week_ids": ["week-002"]},
    ]


def test_teacher_cannot_read_admin_dashboard(repo):
    with pytest.raises(Forbidden, match="requires role admin"):
        get_admin_dashboard(repo, actor_username="teacher01")


def test_teacher_cannot_create_user_profile(repo):
    with pytest.raises(Forbidden, match="requires role admin"):
        create_or_update_user_profile(
            repo,
            actor_username="teacher01",
            username="student-new",
            role="student",
            status="active",
            classes=["jul"],
            allow_profile_only_without_identity=True,
        )


def test_create_user_profile_rejects_invalid_role(repo):
    with pytest.raises(BadRequest, match="invalid role"):
        create_or_update_user_profile(
            repo,
            actor_username="admin01",
            username="student-new",
            role="owner",
            status="active",
            classes=["jul"],
            allow_profile_only_without_identity=True,
        )


def test_create_user_profile_rejects_invalid_status(repo):
    with pytest.raises(BadRequest, match="invalid status"):
        create_or_update_user_profile(
            repo,
            actor_username="admin01",
            username="student-new",
            role="student",
            status="paused",
            classes=["jul"],
            allow_profile_only_without_identity=True,
        )


def test_create_user_profile_rejects_invalid_class(repo):
    with pytest.raises(BadRequest, match="invalid classes: sep"):
        create_or_update_user_profile(
            repo,
            actor_username="admin01",
            username="student-new",
            role="student",
            status="active",
            classes=["jul", "sep"],
            allow_profile_only_without_identity=True,
        )


def test_admin_can_open_weeks_for_class(repo):
    result = set_class_open_weeks(
        repo,
        actor_username="admin01",
        class_id="jul",
        open_week_ids=["week-001", "week-003"],
    )

    assert result == {"class_id": "jul", "open_week_ids": ["week-001", "week-003"]}
    assert repo.get_class_access("jul").open_week_ids == ["week-001", "week-003"]


def test_admin_can_read_open_weeks_for_class(repo):
    result = list_class_open_weeks(repo, actor_username="admin01", class_id="jul")

    assert result == {"class_id": "jul", "open_week_ids": ["week-001"]}


def test_read_open_weeks_rejects_invalid_class(repo):
    with pytest.raises(BadRequest, match="invalid class_id"):
        list_class_open_weeks(repo, actor_username="admin01", class_id="sep")


def test_teacher_cannot_open_weeks_for_class(repo):
    with pytest.raises(Forbidden, match="requires role admin"):
        set_class_open_weeks(
            repo,
            actor_username="teacher01",
            class_id="jul",
            open_week_ids=["week-001"],
        )


def test_set_class_open_weeks_rejects_invalid_class(repo):
    with pytest.raises(BadRequest, match="invalid class_id"):
        set_class_open_weeks(
            repo,
            actor_username="admin01",
            class_id="sep",
            open_week_ids=["week-001"],
        )


def test_set_class_open_weeks_rejects_unknown_week(repo):
    with pytest.raises(BadRequest, match="unknown week ids: week-999"):
        set_class_open_weeks(
            repo,
            actor_username="admin01",
            class_id="jul",
            open_week_ids=["week-001", "week-999"],
        )


def test_admin_class_open_weeks_rejects_other_class_scoped_week(repo):
    repo.save_week(
        Week(
            week_id="jul-week-001",
            week_number=1,
            title="七月主題",
            class_id="jul",
        )
    )

    with pytest.raises(BadRequest, match="week ids do not belong to class aug"):
        set_class_open_weeks(
            repo,
            actor_username="admin01",
            class_id="aug",
            open_week_ids=["jul-week-001"],
        )


def _http_api_event(username: str, method: str, path: str, *, body=None, headers=None):
    return {
        "requestContext": {
            "http": {"method": method},
            "authorizer": {"jwt": {"claims": {"cognito:username": username}}},
        },
        "rawPath": path,
        "body": json.dumps(body) if body is not None else None,
        "headers": headers or {},
    }


def test_make_response_serializes_json():
    from magic_api.app import make_response

    response = make_response(200, {"ok": True})

    assert response["statusCode"] == 200
    assert response["headers"]["content-type"] == "application/json"
    assert json.loads(response["body"]) == {"ok": True}


def test_options_response_does_not_require_jwt_claims(repo):
    from magic_api.app import route

    response = route(
        {
            "requestContext": {"http": {"method": "OPTIONS"}},
            "rawPath": "/student/weeks",
            "headers": {"Origin": "https://admin.example.com"},
        },
        repo,
    )

    assert response["statusCode"] == 204
    assert response["headers"]["access-control-allow-origin"] == "https://admin.example.com"
    assert "authorization" in response["headers"]["access-control-allow-headers"]


def test_route_serves_admin_dashboard(repo):
    from magic_api.app import route

    response = route(_http_api_event("admin01", "GET", "/admin/dashboard"), repo)

    assert response["statusCode"] == 200
    payload = _response_body(response)
    assert sorted(payload.keys()) == ["class_access", "users", "weeks"]
    assert [user["username"] for user in payload["users"]] == [
        "admin01",
        "student-aug",
        "student-both",
        "student-jul",
        "teacher01",
    ]


def test_student_weeks_route_passes_device_id_header(repo):
    from magic_api.app import route

    response = route(
        _http_api_event(
            "student-jul",
            "GET",
            "/student/weeks",
            headers={"X-Device-Id": "device-jul"},
        ),
        repo,
    )

    assert response["statusCode"] == 200
    weeks = json.loads(response["body"])
    assert [week["week_id"] for week in weeks] == ["week-001", "week-002", "week-003"]
    assert [week["week_id"] for week in weeks if week["is_open"]] == ["week-001"]


def test_student_class_weeks_route_filters_to_requested_class(repo):
    from magic_api.app import route

    response = route(
        _http_api_event(
            "student-both",
            "GET",
            "/student/classes/aug/weeks",
            headers={"x-device-id": "device-both"},
        ),
        repo,
    )

    assert response["statusCode"] == 200
    weeks = json.loads(response["body"])
    assert [week["week_id"] for week in weeks] == ["week-001", "week-002", "week-003"]
    assert [week["week_id"] for week in weeks if week["is_open"]] == ["week-002"]


def test_student_class_weeks_route_rejects_unassigned_class(repo):
    from magic_api.app import handle_errors, route

    response = handle_errors(
        lambda: route(
            _http_api_event(
                "student-jul",
                "GET",
                "/student/classes/aug/weeks",
                headers={"x-device-id": "device-jul"},
            ),
            repo,
        )
    )

    assert response["statusCode"] == 403
    assert _response_body(response)["message"] == "student does not belong to this class"


def test_admin_class_open_weeks_route_returns_current_selection(repo):
    from magic_api.app import route

    response = route(_http_api_event("admin01", "GET", "/admin/classes/jul/open-weeks"), repo)

    assert response["statusCode"] == 200
    assert _response_body(response) == {"class_id": "jul", "open_week_ids": ["week-001"]}


def test_teacher_content_assets_route_returns_s3_options(repo, monkeypatch):
    import magic_api.app as app

    monkeypatch.setattr(
        app,
        "_CONTENT_KEYS_FACTORY",
        lambda: [
            "pdf/Week 1 Intro.pdf",
            "magic-pages/mindreading.html",
        ],
    )
    monkeypatch.setattr(app, "_PDF_URL_FACTORY", lambda key: f"https://signed.example/{key}")

    response = app.route(_http_api_event("teacher01", "GET", "/teacher/content-assets"), repo)

    assert response["statusCode"] == 200
    assert _response_body(response)["magic_pages"][0] == {
        "key": "magic-pages/mindreading.html",
        "name": "mindreading.html",
        "url": "https://signed.example/magic-pages/mindreading.html",
    }


def _response_body(response):
    return json.loads(response["body"])


def test_route_rejects_malformed_json_body(repo):
    from magic_api.app import handle_errors, route

    event = _http_api_event("teacher01", "POST", "/teacher/weeks", body={"title": "Week 4"})
    event["body"] = "{not-json"

    response = handle_errors(lambda: route(event, repo))

    assert response["statusCode"] == 400
    assert _response_body(response) == {"error": "bad_request", "message": "invalid JSON body"}


@pytest.mark.parametrize("body", ['["not", "object"]', '"not-object"', "123"])
def test_route_rejects_non_object_json_body(repo, body):
    from magic_api.app import handle_errors, route

    event = _http_api_event("teacher01", "POST", "/teacher/weeks")
    event["body"] = body

    response = handle_errors(lambda: route(event, repo))

    assert response["statusCode"] == 400
    assert _response_body(response) == {
        "error": "bad_request",
        "message": "JSON body must be an object",
    }


def test_create_week_route_rejects_missing_title(repo):
    from magic_api.app import handle_errors, route

    response = handle_errors(
        lambda: route(
            _http_api_event("teacher01", "POST", "/teacher/weeks", body={"week_number": 4}), repo
        )
    )

    assert response["statusCode"] == 400
    assert _response_body(response) == {
        "error": "bad_request",
        "message": "missing required field: title",
    }


@pytest.mark.parametrize("week_number", ["abc", None])
def test_create_week_route_rejects_invalid_week_number(repo, week_number):
    from magic_api.app import handle_errors, route

    response = handle_errors(
        lambda: route(
            _http_api_event(
                "teacher01",
                "POST",
                "/teacher/weeks",
                body={"week_number": week_number, "title": "Week 4"},
            ),
            repo,
        )
    )

    assert response["statusCode"] == 400
    assert _response_body(response) == {
        "error": "bad_request",
        "message": "week_number must be an integer",
    }


def test_handle_errors_returns_generic_internal_error_body():
    from magic_api.app import handle_errors

    response = handle_errors(lambda: (_ for _ in ()).throw(RuntimeError("secret details")))

    assert response["statusCode"] == 500
    assert _response_body(response) == {
        "error": "internal_error",
        "message": "internal server error",
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/student/weeks/week-001/extra"),
        ("GET", "/teacher/weeks/week-001/extra"),
        ("PATCH", "/teacher/weeks/week-001/extra"),
        ("PUT", "/admin/classes/jul/open-weeks/extra"),
    ],
)
def test_routes_reject_extra_path_segments(repo, method, path):
    from magic_api.app import handle_errors, route

    username = "student-jul" if path.startswith("/student") else "teacher01"
    if path.startswith("/admin"):
        username = "admin01"
    response = handle_errors(lambda: route(_http_api_event(username, method, path), repo))

    assert response["statusCode"] == 404
    assert _response_body(response)["error"] == "not_found"


class FakeIdentityAdmin:
    def __init__(self):
        self.calls = []

    def upsert_user(self, *, username, role, status, temporary_password):
        self.calls.append({
            "username": username,
            "role": role,
            "status": status,
            "temporary_password": temporary_password,
        })


class FailingSaveRepository:
    def __init__(self, wrapped, *, fail_on_save_number: int):
        self.wrapped = wrapped
        self.fail_on_save_number = fail_on_save_number
        self.save_calls = 0

    def get_user(self, username):
        return self.wrapped.get_user(username)

    def save_user(self, profile):
        self.save_calls += 1
        if self.save_calls == self.fail_on_save_number:
            raise RuntimeError("simulated profile persistence failure")
        self.wrapped.save_user(profile)

    def list_users(self):
        return self.wrapped.list_users()

    def get_week(self, week_id):
        return self.wrapped.get_week(week_id)

    def list_weeks(self):
        return self.wrapped.list_weeks()

    def save_week(self, week):
        self.wrapped.save_week(week)

    def get_class_access(self, class_id):
        return self.wrapped.get_class_access(class_id)

    def save_class_access(self, access):
        self.wrapped.save_class_access(access)


def test_admin_identity_sync_repairs_existing_profile(repo):
    identity = FakeIdentityAdmin()
    repo.users["student-jul"].identity_sync_status = "failed"
    repo.users["student-jul"].identity_sync_error = "previous sync failure"

    result = sync_user_identity(
        repo,
        actor_username="admin01",
        username="student-jul",
        identity_admin=identity,
    )

    assert result == {"username": "student-jul", "status": "identity_synced"}
    assert repo.get_user("student-jul").identity_sync_status == "synced"
    assert repo.get_user("student-jul").identity_sync_error is None
    assert identity.calls == [{
        "username": "student-jul",
        "role": "student",
        "status": "active",
        "temporary_password": None,
    }]


def test_admin_identity_sync_route_uses_existing_profile(monkeypatch, repo):
    import magic_api.app as app

    identity = FakeIdentityAdmin()
    monkeypatch.setattr(app, "_IDENTITY_ADMIN", identity)

    response = app.handle_errors(
        lambda: app.route(
            _http_api_event("admin01", "POST", "/admin/users/student-jul/sync-identity"),
            repo,
        )
    )

    assert response["statusCode"] == 200
    assert _response_body(response) == {"username": "student-jul", "status": "identity_synced"}
    assert identity.calls == [{
        "username": "student-jul",
        "role": "student",
        "status": "active",
        "temporary_password": None,
    }]


def test_identity_sync_reports_missing_temporary_password_for_missing_cognito_user(repo):
    class MissingCognitoUserAdmin(FakeIdentityAdmin):
        def upsert_user(self, *, username, role, status, temporary_password):
            raise ValueError("temporary_password is required for new Cognito users")

    with pytest.raises(BadRequest, match="temporary_password is required for new Cognito users"):
        sync_user_identity(
            repo,
            actor_username="admin01",
            username="student-jul",
            identity_admin=MissingCognitoUserAdmin(),
        )

    assert repo.get_user("student-jul").identity_sync_status == "failed"
    assert (
        repo.get_user("student-jul").identity_sync_error
        == "temporary_password is required for new Cognito users"
    )


def test_admin_profile_creation_syncs_identity_provider(repo):
    identity = FakeIdentityAdmin()
    create_or_update_user_profile(
        repo,
        actor_username="admin01",
        username="student-live",
        role="student",
        status="inactive",
        classes=["jul"],
        temporary_password="TempPassw0rd!",
        identity_admin=identity,
    )
    assert identity.calls == [{
        "username": "student-live",
        "role": "student",
        "status": "inactive",
        "temporary_password": "TempPassw0rd!",
    }]
    assert repo.get_user("student-live").identity_sync_status == "synced"
    assert repo.get_user("student-live").identity_sync_error is None


def test_admin_profile_creation_records_failed_identity_sync(repo):
    class MissingCognitoUserAdmin(FakeIdentityAdmin):
        def upsert_user(self, *, username, role, status, temporary_password):
            raise ValueError("temporary_password is required for new Cognito users")

    with pytest.raises(BadRequest, match="temporary_password is required for new Cognito users"):
        create_or_update_user_profile(
            repo,
            actor_username="admin01",
            username="student-live",
            role="student",
            status="active",
            classes=["jul"],
            identity_admin=MissingCognitoUserAdmin(),
        )

    profile = repo.get_user("student-live")
    assert profile.identity_sync_status == "failed"
    assert profile.identity_sync_error == "temporary_password is required for new Cognito users"


def test_admin_profile_creation_records_service_identity_sync_failure(repo):
    class ServiceFailingIdentityAdmin(FakeIdentityAdmin):
        def upsert_user(self, *, username, role, status, temporary_password):
            raise RuntimeError("cognito throttled")

    with pytest.raises(BadRequest, match="cognito throttled"):
        create_or_update_user_profile(
            repo,
            actor_username="admin01",
            username="student-live",
            role="admin",
            status="active",
            classes=[],
            identity_admin=ServiceFailingIdentityAdmin(),
        )

    profile = repo.get_user("student-live")
    assert profile.role == "admin"
    assert profile.identity_sync_status == "failed"
    assert profile.identity_sync_error == "cognito throttled"
    with pytest.raises(Forbidden, match="identity sync is not complete"):
        list_user_profiles(repo, actor_username="student-live")


def test_admin_profile_creation_does_not_mutate_identity_when_initial_profile_save_fails(repo):
    identity = FakeIdentityAdmin()
    failing_repo = FailingSaveRepository(repo, fail_on_save_number=1)

    with pytest.raises(RuntimeError, match="simulated profile persistence failure"):
        create_or_update_user_profile(
            failing_repo,
            actor_username="admin01",
            username="student-live",
            role="student",
            status="active",
            classes=["jul"],
            temporary_password="TempPassw0rd!",
            identity_admin=identity,
        )

    assert identity.calls == []
    with pytest.raises(NotFound):
        repo.get_user("student-live")


def test_admin_profile_creation_leaves_pending_record_if_final_commit_fails(repo):
    identity = FakeIdentityAdmin()
    failing_repo = FailingSaveRepository(repo, fail_on_save_number=2)

    with pytest.raises(RuntimeError, match="simulated profile persistence failure"):
        create_or_update_user_profile(
            failing_repo,
            actor_username="admin01",
            username="student-live",
            role="student",
            status="active",
            classes=["jul"],
            temporary_password="TempPassw0rd!",
            identity_admin=identity,
        )

    profile = repo.get_user("student-live")
    assert profile == UserProfile(
        username="student-live",
        role="student",
        status="active",
        classes=["jul"],
        identity_sync_status="pending",
    )
    assert identity.calls == [{
        "username": "student-live",
        "role": "student",
        "status": "active",
        "temporary_password": "TempPassw0rd!",
    }]
    with pytest.raises(Forbidden, match="identity sync is not complete"):
        list_user_profiles(repo, actor_username="student-live")


class FakePasswordResetAdmin:
    def __init__(self):
        self.calls = []

    def reset_password(self, *, username, temporary_password):
        self.calls.append({"username": username, "temporary_password": temporary_password})


def test_admin_password_reset_has_dedicated_identity_only_route(repo):
    from magic_api.routes_admin import reset_user_password

    identity = FakePasswordResetAdmin()
    before = repo.get_user("student-jul")

    result = reset_user_password(
        repo,
        actor_username="admin01",
        username="student-jul",
        temporary_password="TempPassw0rd!",
        identity_admin=identity,
    )

    assert result == {"username": "student-jul", "status": "password_reset"}
    assert repo.get_user("student-jul") == before
    assert identity.calls == [{"username": "student-jul", "temporary_password": "TempPassw0rd!"}]


def test_admin_password_reset_rejects_missing_identity_admin(repo):
    from magic_api.errors import BadRequest
    from magic_api.routes_admin import reset_user_password

    try:
        reset_user_password(
            repo,
            actor_username="admin01",
            username="student-jul",
            temporary_password="TempPassw0rd!",
        )
    except BadRequest as exc:
        assert str(exc) == "identity admin is not configured"
    else:
        raise AssertionError("expected missing identity admin to be rejected")


def test_password_reset_route_rejects_missing_temporary_password(repo):
    from magic_api.app import handle_errors, route

    response = handle_errors(
        lambda: route(
            _http_api_event(
                "admin01",
                "POST",
                "/admin/users/password-reset",
                body={"username": "student-jul"},
            ),
            repo,
        )
    )

    assert response["statusCode"] == 400
    assert _response_body(response) == {
        "error": "bad_request",
        "message": "temporary_password is required",
    }


def test_admin_user_route_rejects_missing_identity_admin(repo):
    from magic_api.app import handle_errors, route

    response = handle_errors(
        lambda: route(
            _http_api_event(
                "admin01",
                "POST",
                "/admin/users",
                body={
                    "username": "student-live",
                    "role": "student",
                    "status": "active",
                    "classes": ["jul"],
                    "temporary_password": "TempPassw0rd!",
                },
            ),
            repo,
        )
    )

    assert response["statusCode"] == 400
    assert _response_body(response) == {
        "error": "bad_request",
        "message": "identity admin is not configured",
    }
    with pytest.raises(NotFound):
        repo.get_user("student-live")


def test_handle_errors_logs_api_error_without_success_noise(capsys):
    from magic_api.app import handle_errors
    from magic_api.errors import BadRequest

    response = handle_errors(lambda: (_ for _ in ()).throw(BadRequest("invalid input")))

    captured = capsys.readouterr()
    assert response["statusCode"] == 400
    assert '"event": "api_error"' in captured.err
    assert '"status_code": 400' in captured.err
    assert '"error": "bad_request"' in captured.err
    assert captured.out == ""


def test_handle_errors_does_not_log_success(capsys):
    from magic_api.app import handle_errors

    response = handle_errors(lambda: {"statusCode": 200, "body": "{}"})

    captured = capsys.readouterr()
    assert response["statusCode"] == 200
    assert captured.err == ""
    assert captured.out == ""


def test_teacher_class_open_weeks_route_updates_selection(repo):
    from magic_api.app import route

    response = route(
        _http_api_event(
            "teacher01",
            "PUT",
            "/teacher/classes/jul/open-weeks",
            body={"open_week_ids": ["week-001", "week-003"]},
        ),
        repo,
    )

    assert response["statusCode"] == 200
    assert _response_body(response) == {
        "class_id": "jul",
        "open_week_ids": ["week-001", "week-003"],
    }
    assert repo.get_class_access("jul").open_week_ids == ["week-001", "week-003"]


def test_teacher_class_open_weeks_route_returns_current_selection(repo):
    from magic_api.app import route

    response = route(_http_api_event("teacher01", "GET", "/teacher/classes/aug/open-weeks"), repo)

    assert response["statusCode"] == 200
    assert _response_body(response) == {"class_id": "aug", "open_week_ids": ["week-002"]}


def test_teacher_week_patch_route_accepts_named_url_cards(repo):
    from magic_api.app import route

    response = route(
        _http_api_event(
            "teacher01",
            "PATCH",
            "/teacher/weeks/week-001",
            body={
                "title": "讀心術",
                "magic_pages": ["mindreading.html"],
                "url_cards": [{"name": "外部補充", "url": "https://example.com/more"}],
            },
        ),
        repo,
    )

    assert response["statusCode"] == 200
    assert _response_body(response)["url_cards"] == [
        {"name": "外部補充", "url": "https://example.com/more"}
    ]
    assert repo.get_week("week-001").url_cards == [
        {"name": "外部補充", "url": "https://example.com/more"}
    ]


def test_teacher_week_delete_route_hard_deletes_week_and_access(repo):
    from magic_api.app import route
    from magic_api.errors import NotFound

    response = route(_http_api_event("teacher01", "DELETE", "/teacher/weeks/week-001"), repo)

    assert response["statusCode"] == 200
    assert _response_body(response) == {"week_id": "week-001", "status": "deleted"}
    with pytest.raises(NotFound):
        repo.get_week("week-001")
    assert repo.get_class_access("jul").open_week_ids == []


class FakeDeleteIdentityAdmin(FakeIdentityAdmin):
    def delete_user(self, *, username):
        self.calls.append({"delete_username": username})


def test_admin_can_delete_user_profile_and_identity(repo):
    from magic_api.routes_admin import delete_user_profile

    identity = FakeDeleteIdentityAdmin()

    result = delete_user_profile(
        repo,
        actor_username="admin01",
        username="student-jul",
        identity_admin=identity,
    )

    assert result == {"username": "student-jul", "status": "deleted"}
    assert identity.calls == [{"delete_username": "student-jul"}]
    with pytest.raises(NotFound):
        repo.get_user("student-jul")


def test_admin_cannot_delete_own_profile(repo):
    from magic_api.routes_admin import delete_user_profile

    with pytest.raises(BadRequest, match="cannot delete own account"):
        delete_user_profile(
            repo,
            actor_username="admin01",
            username="admin01",
            identity_admin=FakeDeleteIdentityAdmin(),
        )


def test_delete_user_route_deletes_profile_and_identity(monkeypatch, repo):
    import magic_api.app as app

    identity = FakeDeleteIdentityAdmin()
    monkeypatch.setattr(app, "_IDENTITY_ADMIN", identity)

    response = app.route(_http_api_event("admin01", "DELETE", "/admin/users/student-jul"), repo)

    assert response["statusCode"] == 200
    assert _response_body(response) == {"username": "student-jul", "status": "deleted"}
    assert identity.calls == [{"delete_username": "student-jul"}]
    with pytest.raises(NotFound):
        repo.get_user("student-jul")


def test_teacher_image_upload_route_returns_presigned_put_url(repo, monkeypatch):
    import magic_api.app as app

    monkeypatch.setattr(
        app,
        "_IMAGE_UPLOAD_URL_FACTORY",
        lambda key, content_type: f"https://upload.example/{key}?type={content_type}",
    )

    response = app.route(
        _http_api_event(
            "teacher01",
            "POST",
            "/teacher/weeks/week-001/image-upload",
            body={"filename": "課堂 白板.png", "content_type": "image/png"},
        ),
        repo,
    )

    assert response["statusCode"] == 200
    body = _response_body(response)
    assert body["image_key"].startswith("images/week-001/")
    assert body["image_key"].endswith("-課堂-白板.png")
    assert body["content_type"] == "image/png"
    assert body["upload_url"] == f"https://upload.example/{body['image_key']}?type=image/png"


def test_week_patch_route_accepts_image_cards(repo):
    from magic_api.app import route

    response = route(
        _http_api_event(
            "teacher01",
            "PATCH",
            "/teacher/weeks/week-001",
            body={
                "image_cards": [
                    {
                        "name": "課堂白板",
                        "image_key": "images/week-001/board.webp",
                        "content_type": "image/webp",
                    }
                ]
            },
        ),
        repo,
    )

    assert response["statusCode"] == 200
    assert _response_body(response)["image_cards"] == [
        {
            "name": "課堂白板",
            "image_key": "images/week-001/board.webp",
            "content_type": "image/webp",
        }
    ]
