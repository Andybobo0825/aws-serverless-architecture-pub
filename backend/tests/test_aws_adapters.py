import importlib
import sys

import pytest

from magic_api.errors import BadRequest
from magic_api.models import ClassAccess, UserProfile, Week


class FakeTable:
    def __init__(self, key_name: str):
        self.key_name = key_name
        self.items = {}

    def get_item(self, *, Key):
        key = Key[self.key_name]
        item = self.items.get(key)
        return {"Item": item} if item is not None else {}

    def put_item(self, *, Item):
        self.items[Item[self.key_name]] = dict(Item)

    def delete_item(self, *, Key):
        self.items.pop(Key[self.key_name], None)

    def scan(self, **_kwargs):
        return {"Items": list(self.items.values())}


class FakePaginatedTable:
    def __init__(self, pages):
        self.pages = pages
        self.scan_calls = []

    def scan(self, **kwargs):
        self.scan_calls.append(dict(kwargs))
        return self.pages[len(self.scan_calls) - 1]


class FakeDynamoResource:
    def __init__(self):
        self.tables = {
            "users": FakeTable("username"),
            "weeks": FakeTable("week_id"),
            "access": FakeTable("class_id"),
        }

    def Table(self, name):  # noqa: N802 - mirrors boto3 resource API
        return self.tables[name]


class FakeCustomDynamoResource:
    def __init__(self, *, users_table, weeks_table):
        self.tables = {
            "users": users_table,
            "weeks": weeks_table,
            "access": FakeTable("class_id"),
        }

    def Table(self, name):  # noqa: N802 - mirrors boto3 resource API
        return self.tables[name]


def test_dynamodb_repository_round_trips_models_and_defaults_missing_class_access():
    from magic_api.repositories import DynamoDbRepository

    resource = FakeDynamoResource()
    repo = DynamoDbRepository(
        resource,
        users_table="users",
        weeks_table="weeks",
        class_access_table="access",
    )

    repo.save_user(UserProfile(username="student-jul", role="student", classes=["jul"]))
    repo.save_week(Week(week_id="week-001", week_number=1, title="Week 1"))
    repo.save_class_access(ClassAccess(class_id="jul", open_week_ids=["week-001"]))

    assert repo.get_user("student-jul") == UserProfile(
        username="student-jul", role="student", classes=["jul"]
    )
    assert repo.get_week("week-001") == Week(week_id="week-001", week_number=1, title="Week 1")
    assert repo.get_class_access("jul") == ClassAccess(
        class_id="jul", open_week_ids=["week-001"]
    )
    assert repo.get_class_access("aug") == ClassAccess(class_id="aug", open_week_ids=[])


def test_dynamodb_repository_hard_deletes_week_item():
    from magic_api.errors import NotFound
    from magic_api.repositories import DynamoDbRepository

    resource = FakeDynamoResource()
    repo = DynamoDbRepository(
        resource,
        users_table="users",
        weeks_table="weeks",
        class_access_table="access",
    )
    repo.save_week(Week(week_id="week-001", week_number=1, title="Week 1"))

    repo.delete_week("week-001")

    with pytest.raises(NotFound):
        repo.get_week("week-001")


def test_dynamodb_repository_rejects_invalid_class_id_from_item():
    from magic_api.repositories import DynamoDbRepository

    resource = FakeDynamoResource()
    resource.tables["access"].items["jul"] = {"class_id": "sep", "open_week_ids": []}
    repo = DynamoDbRepository(
        resource,
        users_table="users",
        weeks_table="weeks",
        class_access_table="access",
    )

    with pytest.raises(BadRequest, match="invalid class_id"):
        repo.get_class_access("jul")


def test_dynamodb_repository_list_users_reads_all_scan_pages_and_passes_exclusive_start_key():
    from magic_api.repositories import DynamoDbRepository

    users_table = FakePaginatedTable(
        [
            {
                "Items": [
                    {"username": "student-b", "role": "student", "classes": ["jul"]},
                ],
                "LastEvaluatedKey": {"username": "student-b"},
            },
            {
                "Items": [
                    {"username": "student-a", "role": "student", "classes": ["aug"]},
                ],
            },
        ]
    )
    resource = FakeCustomDynamoResource(users_table=users_table, weeks_table=FakeTable("week_id"))
    repo = DynamoDbRepository(
        resource,
        users_table="users",
        weeks_table="weeks",
        class_access_table="access",
    )

    assert [user.username for user in repo.list_users()] == ["student-a", "student-b"]
    assert users_table.scan_calls == [{}, {"ExclusiveStartKey": {"username": "student-b"}}]


def test_dynamodb_repository_list_weeks_reads_all_scan_pages_and_passes_exclusive_start_key():
    from magic_api.repositories import DynamoDbRepository

    weeks_table = FakePaginatedTable(
        [
            {
                "Items": [
                    {"week_id": "week-002", "week_number": 2, "title": "Week 2"},
                ],
                "LastEvaluatedKey": {"week_id": "week-002"},
            },
            {
                "Items": [
                    {"week_id": "week-001", "week_number": 1, "title": "Week 1"},
                ],
            },
        ]
    )
    resource = FakeCustomDynamoResource(users_table=FakeTable("username"), weeks_table=weeks_table)
    repo = DynamoDbRepository(
        resource,
        users_table="users",
        weeks_table="weeks",
        class_access_table="access",
    )

    assert [week.week_id for week in repo.list_weeks()] == ["week-001", "week-002"]
    assert weeks_table.scan_calls == [{}, {"ExclusiveStartKey": {"week_id": "week-002"}}]


@pytest.mark.parametrize(
    ("method_name", "table_name"),
    [("list_users", "users"), ("list_weeks", "weeks")],
)
def test_dynamodb_repository_scan_rejects_non_mapping_items(method_name, table_name):
    from magic_api.repositories import DynamoDbRepository

    table = FakePaginatedTable([{"Items": [object()]}])
    resource = FakeCustomDynamoResource(
        users_table=table if table_name == "users" else FakeTable("username"),
        weeks_table=table if table_name == "weeks" else FakeTable("week_id"),
    )
    repo = DynamoDbRepository(
        resource,
        users_table="users",
        weeks_table="weeks",
        class_access_table="access",
    )

    with pytest.raises(BadRequest, match=f"invalid {table_name} scan item"):
        getattr(repo, method_name)()


def test_build_repository_uses_in_memory_without_aws_env_or_boto3(monkeypatch):
    monkeypatch.delenv("USERS_TABLE_NAME", raising=False)
    monkeypatch.delenv("WEEKS_TABLE_NAME", raising=False)
    monkeypatch.delenv("CLASS_ACCESS_TABLE_NAME", raising=False)
    monkeypatch.delenv("CONTENT_BUCKET_NAME", raising=False)
    sys.modules.pop("boto3", None)

    app = importlib.reload(importlib.import_module("magic_api.app"))

    assert app.build_repository_from_env().__class__.__name__ == "InMemoryRepository"
    assert "boto3" not in sys.modules


def test_load_settings_reads_runtime_env(monkeypatch):
    monkeypatch.setenv("USERS_TABLE_NAME", "users")
    monkeypatch.setenv("WEEKS_TABLE_NAME", "weeks")
    monkeypatch.setenv("CLASS_ACCESS_TABLE_NAME", "access")
    monkeypatch.setenv("CONTENT_BUCKET_NAME", "content")
    monkeypatch.setenv("PDF_URL_TTL_SECONDS", "600")

    from magic_api.config import load_settings

    settings = load_settings()

    assert settings.users_table == "users"
    assert settings.weeks_table == "weeks"
    assert settings.class_access_table == "access"
    assert settings.content_bucket == "content"
    assert settings.pdf_url_ttl_seconds == 600


class FakeS3Client:
    def generate_presigned_url(self, operation, *, Params, ExpiresIn):  # noqa: N803 - boto3 API
        content_type = Params.get("ContentType", "")
        return f"{operation}:{Params['Bucket']}:{Params['Key']}:{ExpiresIn}:{content_type}"


def test_s3_signing_helpers_validate_keys_and_delegate_to_client():
    from magic_api.s3_signing import create_presigned_get_url, create_presigned_put_url

    client = FakeS3Client()

    assert create_presigned_get_url(
        client, bucket="content", key="pdf/week-001.pdf", expires_in=120
    ) == "get_object:content:pdf/week-001.pdf:120:"
    assert create_presigned_put_url(
        client, bucket="content", key="pdf/week-001.pdf", expires_in=300
    ) == "put_object:content:pdf/week-001.pdf:300:application/pdf"
    with pytest.raises(BadRequest, match="content key is not configured"):
        create_presigned_get_url(client, bucket="content", key=None, expires_in=120)
    with pytest.raises(BadRequest, match="upload key is required"):
        create_presigned_put_url(client, bucket="content", key="")
