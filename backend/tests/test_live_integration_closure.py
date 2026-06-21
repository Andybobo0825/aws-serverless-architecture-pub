from __future__ import annotations

import importlib
import sys
from pathlib import Path

from magic_api.cognito_admin import CognitoIdentityAdmin
from magic_api.routes_student import get_student_week_detail
from magic_api.routes_teacher import get_teacher_week_detail

ROOT = Path(__file__).resolve().parents[2]


class FakeBoto3:
    def __init__(self) -> None:
        self.clients: list[str] = []

    def client(self, name: str):
        self.clients.append(name)
        return object()


def test_lambda_identity_admin_factory_uses_cognito_pool_env_and_keyword_constructor(monkeypatch):
    monkeypatch.delenv("USERS_TABLE_NAME", raising=False)
    monkeypatch.delenv("WEEKS_TABLE_NAME", raising=False)
    monkeypatch.delenv("CLASS_ACCESS_TABLE_NAME", raising=False)
    monkeypatch.delenv("CONTENT_BUCKET_NAME", raising=False)
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "pool-live")
    fake_boto3 = FakeBoto3()
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    app = importlib.reload(importlib.import_module("magic_api.app"))

    identity_admin = app.build_identity_admin_from_env()

    assert identity_admin.__class__.__name__ == "CognitoIdentityAdmin"
    assert identity_admin.user_pool_id == "pool-live"
    assert fake_boto3.clients
    assert all(client == "cognito-idp" for client in fake_boto3.clients)


class ExistingUserCognitoClient:
    class exceptions:
        class UserNotFoundException(Exception):
            pass

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def admin_get_user(self, **kwargs):
        self.calls.append(("admin_get_user", kwargs))
        return {"Username": kwargs["Username"]}

    def admin_create_user(self, **kwargs):
        self.calls.append(("admin_create_user", kwargs))

    def admin_set_user_password(self, **kwargs):
        self.calls.append(("admin_set_user_password", kwargs))

    def admin_list_groups_for_user(self, **kwargs):
        self.calls.append(("admin_list_groups_for_user", kwargs))
        return {"Groups": []}

    def admin_add_user_to_group(self, **kwargs):
        self.calls.append(("admin_add_user_to_group", kwargs))

    def admin_remove_user_from_group(self, **kwargs):
        self.calls.append(("admin_remove_user_from_group", kwargs))

    def admin_disable_user(self, **kwargs):
        self.calls.append(("admin_disable_user", kwargs))

    def admin_enable_user(self, **kwargs):
        self.calls.append(("admin_enable_user", kwargs))

    def admin_delete_user(self, **kwargs):
        self.calls.append(("admin_delete_user", kwargs))


def test_cognito_admin_resets_existing_user_temporary_password():
    client = ExistingUserCognitoClient()
    admin = CognitoIdentityAdmin(client, user_pool_id="pool-live")

    admin.upsert_user(
        username="student001",
        role="student",
        status="active",
        temporary_password="TempPassw0rd!",
    )

    assert "admin_create_user" not in [name for name, _kwargs in client.calls]
    assert (
        "admin_set_user_password",
        {
            "UserPoolId": "pool-live",
            "Username": "student001",
            "Password": "TempPassw0rd!",
            "Permanent": False,
        },
    ) in client.calls


def test_cognito_admin_delete_user_is_idempotent_when_identity_is_already_missing():
    class MissingUserCognitoClient(ExistingUserCognitoClient):
        def admin_delete_user(self, **kwargs):
            self.calls.append(("admin_delete_user", kwargs))
            raise self.exceptions.UserNotFoundException()

    client = MissingUserCognitoClient()
    admin = CognitoIdentityAdmin(client, user_pool_id="pool-live")

    admin.delete_user(username="student001")

    assert client.calls == [
        (
            "admin_delete_user",
            {"UserPoolId": "pool-live", "Username": "student001"},
        )
    ]


def test_authorized_student_week_detail_returns_signed_magic_page_urls(repo):
    repo.weeks["week-001"].magic_pages = ["mindreading.html", "時鐘/碼表.html"]

    result = get_student_week_detail(
        repo,
        "student-jul",
        "week-001",
        "device-jul",
        magic_page_url_factory=lambda key: f"https://signed.example/{key}",
    )

    assert result["magic_page_urls"] == [
        {"name": "mindreading.html", "url": "https://signed.example/magic-pages/mindreading.html"},
        {"name": "時鐘/碼表.html", "url": "https://signed.example/magic-pages/時鐘/碼表.html"},
    ]


def test_teacher_week_detail_returns_signed_magic_page_urls(repo):
    repo.weeks["week-001"].magic_pages = ["mindreading.html"]

    result = get_teacher_week_detail(
        repo,
        actor_username="teacher01",
        week_id="week-001",
        magic_page_url_factory=lambda key: f"https://signed.example/{key}",
    )

    assert result["magic_page_urls"] == [
        {"name": "mindreading.html", "url": "https://signed.example/magic-pages/mindreading.html"}
    ]


class GroupedCognitoClient(ExistingUserCognitoClient):
    def admin_list_groups_for_user(self, **kwargs):
        self.calls.append(("admin_list_groups_for_user", kwargs))
        return {"Groups": [{"GroupName": "teacher"}, {"GroupName": "admin"}]}

    def admin_remove_user_from_group(self, **kwargs):
        self.calls.append(("admin_remove_user_from_group", kwargs))


def test_cognito_admin_reconciles_user_to_exactly_one_role_group():
    client = GroupedCognitoClient()
    admin = CognitoIdentityAdmin(client, user_pool_id="pool-live")

    admin.upsert_user(
        username="user01",
        role="student",
        status="active",
        temporary_password=None,
    )

    assert (
        "admin_remove_user_from_group",
        {"UserPoolId": "pool-live", "Username": "user01", "GroupName": "teacher"},
    ) in client.calls
    assert (
        "admin_remove_user_from_group",
        {"UserPoolId": "pool-live", "Username": "user01", "GroupName": "admin"},
    ) in client.calls
    assert (
        "admin_add_user_to_group",
        {"UserPoolId": "pool-live", "Username": "user01", "GroupName": "student"},
    ) in client.calls
