import pytest

from magic_api.errors import Forbidden
from magic_api.routes_student import get_student_week_detail, list_student_weeks


def test_july_student_sees_class_weeks_with_open_flags(repo):
    result = list_student_weeks(repo, "student-jul", "device-jul")
    by_id = {item["week_id"]: item for item in result}

    assert [item["week_id"] for item in result] == ["week-001", "week-002", "week-003"]
    assert by_id["week-001"]["is_open"] is True
    assert by_id["week-002"]["is_open"] is False
    assert by_id["week-003"]["is_open"] is False


def test_august_student_sees_class_weeks_with_open_flags(repo):
    result = list_student_weeks(repo, "student-aug", "device-aug")
    by_id = {item["week_id"]: item for item in result}

    assert [item["week_id"] for item in result] == ["week-001", "week-002", "week-003"]
    assert by_id["week-001"]["is_open"] is False
    assert by_id["week-002"]["is_open"] is True
    assert by_id["week-003"]["is_open"] is False


def test_two_class_student_sees_union(repo):
    result = list_student_weeks(repo, "student-both", "device-both")
    by_id = {item["week_id"]: item for item in result}

    assert [item["week_id"] for item in result] == ["week-001", "week-002", "week-003"]
    assert by_id["week-001"]["is_open"] is True
    assert by_id["week-002"]["is_open"] is True
    assert by_id["week-003"]["is_open"] is False


def test_two_class_student_can_filter_week_list_by_class(repo):
    july = list_student_weeks(repo, "student-both", "device-both", class_id="jul")
    august = list_student_weeks(repo, "student-both", "device-both", class_id="aug")

    assert [item["week_id"] for item in july] == ["week-001", "week-002", "week-003"]
    assert [item["week_id"] for item in july if item["is_open"]] == ["week-001"]
    assert [item["week_id"] for item in august] == ["week-001", "week-002", "week-003"]
    assert [item["week_id"] for item in august if item["is_open"]] == ["week-002"]


def test_student_cannot_filter_week_list_by_unassigned_class(repo):
    with pytest.raises(Forbidden, match="student does not belong to this class"):
        list_student_weeks(repo, "student-jul", "device-jul", class_id="aug")


def test_july_and_august_students_can_open_different_week_one_content(repo):
    from magic_api.models import ClassAccess, Week

    repo.weeks["jul-week-001"] = Week(
        week_id="jul-week-001", week_number=1, title="七月課程", class_id="jul"
    )
    repo.weeks["aug-week-001"] = Week(
        week_id="aug-week-001", week_number=1, title="八月課程", class_id="aug"
    )
    repo.class_access["jul"] = ClassAccess(class_id="jul", open_week_ids=["jul-week-001"])
    repo.class_access["aug"] = ClassAccess(class_id="aug", open_week_ids=["aug-week-001"])

    july = get_student_week_detail(repo, "student-jul", "jul-week-001", "device-jul")
    august = get_student_week_detail(repo, "student-aug", "aug-week-001", "device-aug")

    assert july["title"] == "七月課程"
    assert august["title"] == "八月課程"
    with pytest.raises(Forbidden, match="week is not open for this student"):
        get_student_week_detail(repo, "student-jul", "aug-week-001", "device-jul")


@pytest.mark.parametrize("username", ["teacher01", "admin01"])
def test_list_student_weeks_rejects_non_student_profiles(repo, username):
    with pytest.raises(Forbidden, match="requires role student"):
        list_student_weeks(repo, username, "any-device")


@pytest.mark.parametrize("username", ["teacher01", "admin01"])
def test_get_student_week_detail_rejects_non_student_profiles(repo, username):
    with pytest.raises(Forbidden, match="requires role student"):
        get_student_week_detail(repo, username, "week-001", "any-device")


def test_list_student_weeks_rejects_missing_student_device(repo):
    with pytest.raises(Forbidden, match="student device id is required"):
        list_student_weeks(repo, "student-jul", None)


def test_list_student_weeks_rejects_wrong_student_device(repo):
    with pytest.raises(Forbidden, match="student device is not authorized"):
        list_student_weeks(repo, "student-jul", "wrong-device")


def test_student_with_valid_device_sees_open_week_union(repo):
    result = list_student_weeks(repo, "student-both", "device-both")

    assert [item["week_id"] for item in result if item["is_open"]] == ["week-001", "week-002"]


def test_student_week_list_ignores_stale_open_week_ids(repo):
    from magic_api.models import ClassAccess

    repo.class_access["jul"] = ClassAccess(class_id="jul", open_week_ids=["week-001", "deleted"])

    result = list_student_weeks(repo, "student-jul", "device-jul")

    assert [item["week_id"] for item in result] == ["week-001", "week-002", "week-003"]
    assert [item["week_id"] for item in result if item["is_open"]] == ["week-001"]


def test_student_week_list_prefers_class_scoped_week_over_legacy_template(repo):
    from magic_api.models import ClassAccess, Week

    repo.weeks["jul-week-001"] = Week(
        week_id="jul-week-001", week_number=1, title="七月課程", class_id="jul"
    )
    repo.weeks["aug-week-001"] = Week(
        week_id="aug-week-001", week_number=1, title="八月課程", class_id="aug"
    )
    repo.class_access["jul"] = ClassAccess(class_id="jul", open_week_ids=["jul-week-001"])

    result = list_student_weeks(repo, "student-jul", "device-jul")
    by_id = {item["week_id"]: item for item in result}

    assert [item["week_id"] for item in result] == ["jul-week-001", "week-002", "week-003"]
    assert by_id["jul-week-001"]["is_open"] is True
    assert by_id["week-002"]["is_open"] is False


def test_student_week_detail_returns_signed_pdf_url(repo):
    repo.weeks["week-001"].pdf_s3_key = "pdf/week-001.pdf"
    result = get_student_week_detail(
        repo,
        "student-jul",
        "week-001",
        "device-jul",
        pdf_url_factory=lambda key: f"https://signed.example/{key}",
    )
    assert result["pdf_url"] == "https://signed.example/pdf/week-001.pdf"
    assert "pdf_s3_key" not in result


def test_student_week_detail_returns_named_url_cards(repo):
    repo.weeks["week-001"].url_cards = [{"name": "課後練習", "url": "https://example.com/practice"}]

    result = get_student_week_detail(
        repo,
        "student-jul",
        "week-001",
        "device-jul",
    )

    assert result["url_cards"] == [{"name": "課後練習", "url": "https://example.com/practice"}]
