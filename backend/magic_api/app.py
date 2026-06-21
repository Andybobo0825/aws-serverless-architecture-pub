from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Callable, Mapping
from typing import Any, cast

from magic_api.auth import claims_from_event
from magic_api.cognito_admin import CognitoIdentityAdmin
from magic_api.errors import ApiError, BadRequest, NotFound
from magic_api.repositories import InMemoryRepository, Repository
from magic_api.routes_admin import (
    create_or_update_user_profile,
    delete_user_profile,
    get_admin_dashboard,
    list_class_open_weeks,
    list_user_profiles,
    reset_user_password,
    set_class_open_weeks,
    sync_user_identity,
)
from magic_api.routes_common import get_me, register_device, reset_device
from magic_api.routes_student import get_student_week_detail, list_student_weeks
from magic_api.routes_teacher import (
    create_week,
    create_week_image_upload,
    delete_week,
    get_teacher_dashboard,
    get_teacher_week_detail,
    list_content_assets,
    list_teacher_class_open_weeks,
    list_teacher_weeks,
    set_teacher_class_open_weeks,
    update_week_content,
)
from magic_api.s3_signing import create_presigned_get_url

Json = dict[str, Any]
ALLOWED_CORS_ORIGINS = {
    "https://app.example.com",
    "https://admin.example.com",
}


def make_response(status_code: int, body: object) -> Json:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def make_options_response(event: Json) -> Json:
    headers = _headers(event)
    origin = headers.get("origin")
    response_headers = {
        "access-control-allow-methods": "DELETE,GET,POST,PATCH,PUT,OPTIONS",
        "access-control-allow-headers": "authorization,content-type,x-device-id",
        "access-control-max-age": "3600",
    }
    if origin in ALLOWED_CORS_ORIGINS:
        response_headers["access-control-allow-origin"] = origin
        response_headers["vary"] = "origin"
    return {
        "statusCode": 204,
        "headers": response_headers,
        "body": "",
    }


def read_json(event: Json) -> Json:
    body = event.get("body")
    if not body:
        return {}
    if isinstance(body, str):
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as error:
            raise BadRequest("invalid JSON body") from error
        if not isinstance(decoded, dict):
            raise BadRequest("JSON body must be an object")
        return decoded
    if isinstance(body, dict):
        return body
    raise BadRequest("JSON body must be an object")


def _path_segments(path: str) -> list[str]:
    if path == "/":
        return []
    if not path.startswith("/"):
        return path.split("/")
    return path[1:].split("/")


def _required_value(body: Json, field: str) -> Any:
    if field not in body:
        raise BadRequest(f"missing required field: {field}")
    return body[field]


def _required_int(body: Json, field: str) -> int:
    raw_value = _required_value(body, field)
    if isinstance(raw_value, bool):
        raise BadRequest(f"{field} must be an integer")
    try:
        return int(raw_value)
    except (TypeError, ValueError) as error:
        raise BadRequest(f"{field} must be an integer") from error


def _http_method(event: Json) -> str | None:
    request_context = event.get("requestContext", {})
    if not isinstance(request_context, Mapping):
        return None
    http = request_context.get("http", {})
    if isinstance(http, Mapping):
        method = http.get("method")
        if isinstance(method, str):
            return method
    legacy_method = event.get("httpMethod")
    return legacy_method if isinstance(legacy_method, str) else None


def _headers(event: Json) -> dict[str, str]:
    raw_headers = event.get("headers", {})
    if not isinstance(raw_headers, Mapping):
        return {}
    return {str(key).lower(): str(value) for key, value in raw_headers.items()}


def route(event: Json, repo: Repository) -> Json:
    method = _http_method(event)
    if method == "OPTIONS":
        return make_options_response(event)

    claims = claims_from_event(event)
    path = event.get("rawPath", "/")
    if not isinstance(path, str):
        path = "/"
    segments = _path_segments(path)
    body = read_json(event)
    device_id = _headers(event).get("x-device-id")

    if method == "GET" and path == "/me":
        return make_response(200, get_me(repo, claims.username))
    if method == "POST" and path == "/device/register":
        return make_response(
            200,
            register_device(
                repo,
                actor_username=claims.username,
                target_device_id=str(body.get("device_id", "")),
            ),
        )
    if method == "POST" and path == "/device/reset":
        return make_response(
            200,
            reset_device(
                repo,
                actor_username=claims.username,
                target_username=str(body.get("username", "")),
            ),
        )
    if method == "GET" and path == "/student/weeks":
        return make_response(200, list_student_weeks(repo, claims.username, device_id))
    if (
        method == "GET"
        and len(segments) == 4
        and segments[0] == "student"
        and segments[1] == "classes"
        and segments[2]
        and segments[3] == "weeks"
    ):
        return make_response(
            200,
            list_student_weeks(repo, claims.username, device_id, class_id=segments[2]),
        )
    if method == "GET" and len(segments) == 3 and segments[:2] == ["student", "weeks"]:
        week_id = segments[2]
        return make_response(
            200,
            get_student_week_detail(
                repo,
                claims.username,
                week_id,
                device_id,
                pdf_url_factory=_PDF_URL_FACTORY,
                magic_page_url_factory=_PDF_URL_FACTORY,
            ),
        )
    if method == "GET" and path == "/teacher/weeks":
        return make_response(200, list_teacher_weeks(repo, actor_username=claims.username))
    if (
        method == "GET"
        and len(segments) == 4
        and segments[0] == "teacher"
        and segments[1] == "classes"
        and segments[2]
        and segments[3] == "weeks"
    ):
        return make_response(
            200,
            list_teacher_weeks(repo, actor_username=claims.username, class_id=segments[2]),
        )
    if method == "GET" and path == "/teacher/content-assets":
        return make_response(
            200,
            list_content_assets(
                repo,
                actor_username=claims.username,
                object_keys=_CONTENT_KEYS_FACTORY(),
                pdf_url_factory=_PDF_URL_FACTORY,
                magic_page_url_factory=_PDF_URL_FACTORY,
            ),
        )
    if method == "GET" and path == "/teacher/dashboard":
        return make_response(
            200,
            get_teacher_dashboard(
                repo,
                actor_username=claims.username,
                object_keys=_CONTENT_KEYS_FACTORY(),
                pdf_url_factory=_PDF_URL_FACTORY,
                magic_page_url_factory=_PDF_URL_FACTORY,
            ),
        )
    if method == "GET" and len(segments) == 3 and segments[:2] == ["teacher", "weeks"]:
        week_id = segments[2]
        return make_response(
            200,
            get_teacher_week_detail(
                repo,
                actor_username=claims.username,
                week_id=week_id,
                pdf_url_factory=_PDF_URL_FACTORY,
                pdf_upload_url_factory=_PDF_UPLOAD_URL_FACTORY,
                magic_page_url_factory=_PDF_URL_FACTORY,
            ),
        )
    if method == "POST" and path == "/teacher/weeks":
        return make_response(
            201,
            create_week(
                repo,
                actor_username=claims.username,
                week_number=_required_int(body, "week_number"),
                title=str(_required_value(body, "title")),
                class_id=cast(str | None, body.get("class_id")),
            ),
        )
    if (
        method == "POST"
        and len(segments) == 4
        and segments[0] == "teacher"
        and segments[1] == "classes"
        and segments[2]
        and segments[3] == "weeks"
    ):
        return make_response(
            201,
            create_week(
                repo,
                actor_username=claims.username,
                week_number=_required_int(body, "week_number"),
                title=str(_required_value(body, "title")),
                class_id=segments[2],
            ),
        )
    if method == "PATCH" and len(segments) == 3 and segments[:2] == ["teacher", "weeks"]:
        week_id = segments[2]
        magic_pages = body.get("magic_pages")
        return make_response(
            200,
            update_week_content(
                repo,
                actor_username=claims.username,
                week_id=week_id,
                title=cast(str | None, body.get("title")),
                pdf_s3_key=cast(str | None, body.get("pdf_s3_key")),
                magic_pages=cast(list[str] | None, magic_pages),
                url_cards=cast(list[Any] | None, body.get("url_cards")),
                image_cards=cast(list[Any] | None, body.get("image_cards")),
            ),
        )
    if (
        method == "POST"
        and len(segments) == 4
        and segments[0] == "teacher"
        and segments[1] == "weeks"
        and segments[2]
        and segments[3] == "image-upload"
    ):
        return make_response(
            200,
            create_week_image_upload(
                repo,
                actor_username=claims.username,
                week_id=segments[2],
                filename=str(_required_value(body, "filename")),
                content_type=str(_required_value(body, "content_type")),
                upload_url_factory=_IMAGE_UPLOAD_URL_FACTORY,
            ),
        )
    if method == "DELETE" and len(segments) == 3 and segments[:2] == ["teacher", "weeks"]:
        return make_response(
            200,
            delete_week(
                repo,
                actor_username=claims.username,
                week_id=segments[2],
            ),
        )
    if (
        method == "GET"
        and len(segments) == 4
        and segments[0] == "teacher"
        and segments[1] == "classes"
        and segments[2]
        and segments[3] == "open-weeks"
    ):
        return make_response(
            200,
            list_teacher_class_open_weeks(
                repo,
                actor_username=claims.username,
                class_id=segments[2],
            ),
        )
    if (
        method == "PUT"
        and len(segments) == 4
        and segments[0] == "teacher"
        and segments[1] == "classes"
        and segments[2]
        and segments[3] == "open-weeks"
    ):
        return make_response(
            200,
            set_teacher_class_open_weeks(
                repo,
                actor_username=claims.username,
                class_id=segments[2],
                open_week_ids=cast(list[str], body.get("open_week_ids", [])),
            ),
        )
    if method == "GET" and path == "/admin/users":
        return make_response(200, list_user_profiles(repo, actor_username=claims.username))

    if method == "GET" and path == "/admin/dashboard":
        return make_response(200, get_admin_dashboard(repo, actor_username=claims.username))

    if (
        method == "DELETE"
        and len(segments) == 3
        and segments[0] == "admin"
        and segments[1] == "users"
        and segments[2]
    ):
        return make_response(
            200,
            delete_user_profile(
                repo,
                actor_username=claims.username,
                username=segments[2],
                identity_admin=_IDENTITY_ADMIN,
            ),
        )
    if (
        method == "GET"
        and len(segments) == 4
        and segments[0] == "admin"
        and segments[1] == "classes"
        and segments[2]
        and segments[3] == "open-weeks"
    ):
        return make_response(
            200,
            list_class_open_weeks(
                repo,
                actor_username=claims.username,
                class_id=segments[2],
            ),
        )
    if method == "POST" and path == "/admin/users/password-reset":
        return make_response(
            200,
            reset_user_password(
                repo,
                actor_username=claims.username,
                username=str(_required_value(body, "username")),
                temporary_password=cast(str | None, body.get("temporary_password")),
                identity_admin=_IDENTITY_ADMIN,
            ),
        )
    if (
        method == "POST"
        and len(segments) == 4
        and segments[0] == "admin"
        and segments[1] == "users"
        and segments[2]
        and segments[3] == "sync-identity"
    ):
        return make_response(
            200,
            sync_user_identity(
                repo,
                actor_username=claims.username,
                username=segments[2],
                temporary_password=cast(str | None, body.get("temporary_password")),
                identity_admin=_IDENTITY_ADMIN,
            ),
        )
    if method == "POST" and path == "/admin/users":
        return make_response(
            201,
            create_or_update_user_profile(
                repo,
                actor_username=claims.username,
                username=str(_required_value(body, "username")),
                role=str(_required_value(body, "role")),
                status=str(body.get("status", "active")),
                classes=cast(list[str], body.get("classes", [])),
                temporary_password=cast(str | None, body.get("temporary_password")),
                identity_admin=_IDENTITY_ADMIN,
            ),
        )
    if (
        method == "PUT"
        and len(segments) == 4
        and segments[0] == "admin"
        and segments[1] == "classes"
        and segments[2]
        and segments[3] == "open-weeks"
    ):
        class_id = segments[2]
        return make_response(
            200,
            set_class_open_weeks(
                repo,
                actor_username=claims.username,
                class_id=class_id,
                open_week_ids=cast(list[str], body.get("open_week_ids", [])),
            ),
        )
    raise NotFound(f"route not found: {method} {path}")


def handle_errors(fn: Callable[[], Json]) -> Json:
    try:
        return fn()
    except ApiError as error:
        print(
            json.dumps(
                {
                    "event": "api_error",
                    "status_code": error.status_code,
                    "error": error.code,
                    "message": error.message,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return make_response(error.status_code, {"error": error.code, "message": error.message})
    except Exception as error:
        print(
            json.dumps(
                {
                    "event": "unexpected_error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return make_response(
            500, {"error": "internal_error", "message": "internal server error"}
        )


def build_repository_from_env() -> Repository:
    if "USERS_TABLE_NAME" not in os.environ:
        return InMemoryRepository()

    from magic_api.config import load_settings
    from magic_api.repositories import DynamoDbRepository

    settings = load_settings()
    boto3 = importlib.import_module("boto3")
    dynamodb = boto3.resource("dynamodb")
    return DynamoDbRepository(
        dynamodb,
        users_table=settings.users_table,
        weeks_table=settings.weeks_table,
        class_access_table=settings.class_access_table,
    )


def build_identity_admin_from_env():
    # Only load CognitoAdminIdentity if we're in Lambda with a User Pool
    if "COGNITO_USER_POOL_ID" not in os.environ:
        return None
    boto3 = importlib.import_module("boto3")
    return CognitoIdentityAdmin(
        boto3.client("cognito-idp"),
        user_pool_id=os.environ["COGNITO_USER_POOL_ID"],
    )


def build_pdf_url_factory_from_env():
    if "CONTENT_BUCKET_NAME" not in os.environ:
        return None

    from botocore.config import Config

    from magic_api.config import load_settings

    settings = load_settings()
    boto3 = importlib.import_module("boto3")
    s3_client = boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
        config=Config(signature_version="s3v4"),
    )

    def factory(key: str) -> str:
        return create_presigned_get_url(
            s3_client,
            bucket=settings.content_bucket,
            key=key,
            expires_in=settings.pdf_url_ttl_seconds,
        )
    return factory


def build_pdf_upload_url_factory_from_env():
    if "CONTENT_BUCKET_NAME" not in os.environ:
        return None
    from botocore.config import Config

    from magic_api.config import load_settings
    from magic_api.s3_signing import create_presigned_put_url

    settings = load_settings()
    boto3 = importlib.import_module("boto3")
    s3_client = boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
        config=Config(signature_version="s3v4"),
    )

    def factory(key: str) -> str:
        return create_presigned_put_url(
            s3_client,
            bucket=settings.content_bucket,
            key=key,
            expires_in=settings.pdf_url_ttl_seconds,
        )
    return factory


def build_image_upload_url_factory_from_env():
    if "CONTENT_BUCKET_NAME" not in os.environ:
        return None
    from botocore.config import Config

    from magic_api.config import load_settings
    from magic_api.s3_signing import create_presigned_put_url

    settings = load_settings()
    boto3 = importlib.import_module("boto3")
    s3_client = boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
        config=Config(signature_version="s3v4"),
    )

    def factory(key: str, content_type: str) -> str:
        return create_presigned_put_url(
            s3_client,
            bucket=settings.content_bucket,
            key=key,
            expires_in=settings.pdf_url_ttl_seconds,
            content_type=content_type,
        )
    return factory


def build_content_keys_factory_from_env():
    if "CONTENT_BUCKET_NAME" not in os.environ:
        return lambda: []
    from magic_api.config import load_settings
    from magic_api.s3_signing import list_object_keys

    settings = load_settings()
    boto3 = importlib.import_module("boto3")
    s3_client = boto3.client("s3")

    def factory() -> list[str]:
        return list_object_keys(
            s3_client,
            bucket=settings.content_bucket,
            prefixes=("pdf/", "magic-pages/"),
        )
    return factory


_GLOBAL_REPO = build_repository_from_env()
_IDENTITY_ADMIN = build_identity_admin_from_env()
_PDF_URL_FACTORY = build_pdf_url_factory_from_env()
_PDF_UPLOAD_URL_FACTORY = build_pdf_upload_url_factory_from_env()
_IMAGE_UPLOAD_URL_FACTORY = build_image_upload_url_factory_from_env()
_CONTENT_KEYS_FACTORY = build_content_keys_factory_from_env()


def handler(event: Json, context: object) -> Json:
    return handle_errors(lambda: route(event, _GLOBAL_REPO))
