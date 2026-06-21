import pytest

from magic_api.errors import BadRequest, Forbidden
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


def test_teacher_can_create_week(repo):
    result = create_week(repo, actor_username="teacher01", week_number=4, title="Week 4")

    assert result["week_id"] == "week-004"
    assert result["week_number"] == 4
    assert repo.get_week("week-004").title == "Week 4"


def test_admin_can_create_shared_week_without_opening_class_access(repo):
    result = create_week(repo, actor_username="admin01", week_number=4, title="Week 4")

    assert result["week_id"] == "week-004"
    assert repo.get_class_access("jul").open_week_ids == ["week-001"]
    assert repo.get_class_access("aug").open_week_ids == ["week-002"]


def test_teacher_can_create_july_and_august_week_one_independently(repo):
    july = create_week(
        repo, actor_username="teacher01", week_number=1, title="七月主題", class_id="jul"
    )
    august = create_week(
        repo, actor_username="teacher01", week_number=1, title="八月主題", class_id="aug"
    )

    assert july["week_id"] == "jul-week-001"
    assert july["class_id"] == "jul"
    assert august["week_id"] == "aug-week-001"
    assert august["class_id"] == "aug"
    assert repo.get_week("jul-week-001").title == "七月主題"
    assert repo.get_week("aug-week-001").title == "八月主題"


def test_teacher_hard_deletes_week_and_removes_class_access(repo):
    from magic_api.errors import NotFound

    result = delete_week(repo, actor_username="teacher01", week_id="week-001")

    assert result == {"week_id": "week-001", "status": "deleted"}
    with pytest.raises(NotFound):
        repo.get_week("week-001")
    assert repo.get_class_access("jul").open_week_ids == []
    assert repo.get_class_access("aug").open_week_ids == ["week-002"]
    assert [week["week_id"] for week in list_teacher_weeks(repo, actor_username="teacher01")] == [
        "week-002",
        "week-003",
    ]


def test_student_cannot_hard_delete_week(repo):
    with pytest.raises(Forbidden, match="requires teacher or admin"):
        delete_week(repo, actor_username="student-jul", week_id="week-001")


def test_teacher_class_open_weeks_rejects_other_class_scoped_week(repo):
    create_week(repo, actor_username="teacher01", week_number=1, title="七月主題", class_id="jul")

    with pytest.raises(BadRequest, match="week ids do not belong to class aug"):
        set_teacher_class_open_weeks(
            repo,
            actor_username="teacher01",
            class_id="aug",
            open_week_ids=["jul-week-001"],
        )


def test_teacher_dashboard_combines_class_weeks_access_and_assets(repo):
    result = get_teacher_dashboard(
        repo,
        actor_username="teacher01",
        object_keys=[
            "magic-pages/mindreading.html",
            "magic-pages/時鐘/碼表.html",
            "tmp/ignored.txt",
        ],
        magic_page_url_factory=lambda key: f"https://signed.example/{key}",
    )

    assert result["class_access"] == [
        {"class_id": "jul", "open_week_ids": ["week-001"]},
        {"class_id": "aug", "open_week_ids": ["week-002"]},
    ]
    assert [week["week_id"] for week in result["class_weeks"]["jul"]] == [
        "week-001",
        "week-002",
        "week-003",
    ]
    assert [week["week_id"] for week in result["class_weeks"]["aug"]] == [
        "week-001",
        "week-002",
        "week-003",
    ]
    assert result["assets"]["magic_pages"] == [
        {
            "key": "magic-pages/mindreading.html",
            "name": "mindreading.html",
            "url": "https://signed.example/magic-pages/mindreading.html",
        },
        {
            "key": "magic-pages/時鐘/碼表.html",
            "name": "時鐘/碼表.html",
            "url": "https://signed.example/magic-pages/時鐘/碼表.html",
        },
    ]


def test_student_cannot_read_teacher_dashboard(repo):
    with pytest.raises(Forbidden, match="requires teacher or admin"):
        get_teacher_dashboard(repo, actor_username="student-jul", object_keys=[])


def test_student_cannot_create_week(repo):
    with pytest.raises(Forbidden, match="requires teacher or admin"):
        create_week(repo, actor_username="student-jul", week_number=4, title="Week 4")


def test_rejects_non_positive_week_number(repo):
    with pytest.raises(BadRequest, match="week_number must be positive"):
        create_week(repo, actor_username="teacher01", week_number=0, title="Week 0")


def test_teacher_can_update_pdf_magic_pages_and_url_cards(repo):
    result = update_week_content(
        repo,
        actor_username="teacher01",
        week_id="week-001",
        title="Week 1 Updated",
        pdf_s3_key="pdf/week-001.pdf",
        magic_pages=["mindreading.html", "時鐘/碼表.html"],
        url_cards=[{"name": "補充教材", "url": "https://example.com/lesson"}],
    )

    assert result["title"] == "Week 1 Updated"
    assert result["pdf_s3_key"] == "pdf/week-001.pdf"
    assert result["magic_pages"] == ["mindreading.html", "時鐘/碼表.html"]
    assert result["url_cards"] == [{"name": "補充教材", "url": "https://example.com/lesson"}]


def test_update_accepts_pdf_selected_from_content_bucket(repo):
    result = update_week_content(
        repo,
        actor_username="teacher01",
        week_id="week-001",
        title="Lesson From S3",
        pdf_s3_key="pdf/lesson-one.pdf",
        magic_pages=None,
        url_cards=None,
    )

    assert result["pdf_s3_key"] == "pdf/lesson-one.pdf"
    assert result["title"] == "Lesson From S3"


def test_update_rejects_pdf_key_outside_content_pdf_prefix(repo):
    with pytest.raises(BadRequest, match="pdf_s3_key must be a PDF under pdf/"):
        update_week_content(
            repo,
            actor_username="teacher01",
            week_id="week-001",
            title=None,
            pdf_s3_key="private/other.pdf",
            magic_pages=None,
            url_cards=None,
        )


def test_admin_can_update_shared_week_content_without_opening_class_access(repo):
    result = update_week_content(
        repo,
        actor_username="admin01",
        week_id="week-003",
        title="Week 3 Updated",
        pdf_s3_key="pdf/week-003.pdf",
        magic_pages=["讀心術.html"],
        url_cards=None,
    )

    assert result["title"] == "Week 3 Updated"
    assert repo.get_class_access("jul").open_week_ids == ["week-001"]
    assert repo.get_class_access("aug").open_week_ids == ["week-002"]


def test_student_cannot_update_week_content(repo):
    with pytest.raises(Forbidden, match="requires teacher or admin"):
        update_week_content(
            repo,
            actor_username="student-jul",
            week_id="week-001",
            title="Week 1 Updated",
            pdf_s3_key=None,
            magic_pages=None,
            url_cards=None,
        )


def test_update_accepts_html_magic_page_objects_selected_from_s3(repo):
    result = update_week_content(
        repo,
        actor_username="teacher01",
        week_id="week-001",
        title="calculmagic.html",
        pdf_s3_key=None,
        magic_pages=["calculmagic.html", "nested/lesson.html", "時鐘/碼表.html"],
        url_cards=None,
    )

    assert result["title"] == "calculmagic.html"
    assert result["magic_pages"] == ["calculmagic.html", "nested/lesson.html", "時鐘/碼表.html"]


@pytest.mark.parametrize("page", ["unknown.txt", "../secret.html", "/secret.html", ""])
def test_update_rejects_non_html_or_unsafe_magic_page_objects(repo, page):
    with pytest.raises(BadRequest, match="invalid magic pages"):
        update_week_content(
            repo,
            actor_username="teacher01",
            week_id="week-001",
            title=None,
            pdf_s3_key=None,
            magic_pages=[page],
            url_cards=None,
        )


def test_teacher_lists_all_weeks(repo):
    result = list_teacher_weeks(repo, actor_username="teacher01")

    assert [week["week_id"] for week in result] == ["week-001", "week-002", "week-003"]


def test_teacher_class_week_list_includes_legacy_weeks_as_templates(repo):
    result = list_teacher_weeks(repo, actor_username="teacher01", class_id="jul")

    assert [week["week_id"] for week in result] == ["week-001", "week-002", "week-003"]
    assert all(week["class_id"] is None for week in result)


def test_teacher_class_week_list_prefers_class_scoped_week_over_legacy_template(repo):
    create_week(repo, actor_username="teacher01", week_number=1, title="七月主題", class_id="jul")

    result = list_teacher_weeks(repo, actor_username="teacher01", class_id="jul")

    assert [week["week_id"] for week in result] == ["week-002", "week-003", "jul-week-001"]


def test_student_cannot_list_teacher_weeks(repo):
    with pytest.raises(Forbidden, match="requires teacher or admin"):
        list_teacher_weeks(repo, actor_username="student-jul")


def test_teacher_gets_week_detail_with_signed_pdf(repo):
    repo.weeks["week-001"].pdf_s3_key = "pdf/week-001.pdf"
    result = get_teacher_week_detail(
        repo,
        actor_username="teacher01",
        week_id="week-001",
        pdf_url_factory=lambda key: f"https://signed.example/{key}",
    )
    assert result["week_id"] == "week-001"
    assert result["pdf_url"] == "https://signed.example/pdf/week-001.pdf"


def test_teacher_lists_magic_page_content_assets_from_s3_options(repo):
    result = list_content_assets(
        repo,
        actor_username="teacher01",
        object_keys=[
            "pdf/Week 1 Intro.pdf",
            "magic-pages/mindreading.html",
            "magic-pages/custom-lesson.html",
            "magic-pages/時鐘/碼表.html",
            "tmp/ignored.txt",
        ],
        pdf_url_factory=lambda key: f"https://signed.example/{key}",
        magic_page_url_factory=lambda key: f"https://signed.example/{key}",
    )

    assert result["magic_pages"] == [
        {
            "key": "magic-pages/custom-lesson.html",
            "name": "custom-lesson.html",
            "url": "https://signed.example/magic-pages/custom-lesson.html",
        },
        {
            "key": "magic-pages/mindreading.html",
            "name": "mindreading.html",
            "url": "https://signed.example/magic-pages/mindreading.html",
        },
        {
            "key": "magic-pages/時鐘/碼表.html",
            "name": "時鐘/碼表.html",
            "url": "https://signed.example/magic-pages/時鐘/碼表.html",
        },
    ]


def test_teacher_gets_week_detail_with_named_url_cards(repo):
    repo.weeks["week-001"].url_cards = [{"name": "外部講義", "url": "https://example.com/handout"}]

    result = get_teacher_week_detail(repo, actor_username="teacher01", week_id="week-001")

    assert result["url_cards"] == [{"name": "外部講義", "url": "https://example.com/handout"}]


@pytest.mark.parametrize(
    "url_cards",
    [
        [{"name": "", "url": "https://example.com/lesson"}],
        [{"name": "補充", "url": "javascript:alert(1)"}],
        [{"name": "補充"}],
        ["not-a-card"],
    ],
)
def test_update_rejects_invalid_url_cards(repo, url_cards):
    with pytest.raises(BadRequest, match="invalid url cards"):
        update_week_content(
            repo,
            actor_username="teacher01",
            week_id="week-001",
            title=None,
            pdf_s3_key=None,
            magic_pages=None,
            url_cards=url_cards,
        )


def test_teacher_can_read_open_weeks_for_class(repo):
    result = list_teacher_class_open_weeks(repo, actor_username="teacher01", class_id="jul")

    assert result == {"class_id": "jul", "open_week_ids": ["week-001"]}


def test_teacher_can_open_weeks_for_class(repo):
    result = set_teacher_class_open_weeks(
        repo,
        actor_username="teacher01",
        class_id="aug",
        open_week_ids=["week-001", "week-003"],
    )

    assert result == {"class_id": "aug", "open_week_ids": ["week-001", "week-003"]}
    assert repo.get_class_access("aug").open_week_ids == ["week-001", "week-003"]


def test_student_cannot_open_weeks_for_class_as_teacher(repo):
    with pytest.raises(Forbidden, match="requires teacher or admin"):
        set_teacher_class_open_weeks(
            repo,
            actor_username="student-jul",
            class_id="jul",
            open_week_ids=["week-001"],
        )


def test_teacher_can_update_image_cards(repo):
    result = update_week_content(
        repo,
        actor_username="teacher01",
        week_id="week-001",
        title=None,
        pdf_s3_key=None,
        magic_pages=None,
        url_cards=None,
        image_cards=[
            {
                "name": "課堂白板",
                "image_key": "images/week-001/board.webp",
                "content_type": "image/webp",
            }
        ],
    )

    assert result["image_cards"] == [
        {
            "name": "課堂白板",
            "image_key": "images/week-001/board.webp",
            "content_type": "image/webp",
        }
    ]
    assert repo.get_week("week-001").image_cards == result["image_cards"]


def test_student_week_detail_signs_image_cards(repo):
    from magic_api.routes_student import get_student_week_detail

    repo.weeks["week-001"].image_cards = [
        {
            "name": "課堂白板",
            "image_key": "images/week-001/board.webp",
            "content_type": "image/webp",
        }
    ]

    result = get_student_week_detail(
        repo,
        "student-jul",
        "week-001",
        "device-jul",
        pdf_url_factory=lambda key: f"https://signed.example/{key}",
    )

    assert result["image_cards"] == [
        {
            "name": "課堂白板",
            "image_key": "images/week-001/board.webp",
            "content_type": "image/webp",
            "url": "https://signed.example/images/week-001/board.webp",
        }
    ]


@pytest.mark.parametrize(
    "image_cards",
    [
        [{"name": "", "image_key": "images/week-001/board.webp", "content_type": "image/webp"}],
        [{"name": "白板", "image_key": "pdf/board.webp", "content_type": "image/webp"}],
        [{"name": "白板", "image_key": "images/week-001/board.txt", "content_type": "image/webp"}],
        [
            {
                "name": "白板",
                "image_key": "images/week-001/board.webp",
                "content_type": "application/pdf",
            }
        ],
        ["not-a-card"],
    ],
)
def test_update_rejects_invalid_image_cards(repo, image_cards):
    with pytest.raises(BadRequest, match="invalid image cards"):
        update_week_content(
            repo,
            actor_username="teacher01",
            week_id="week-001",
            title=None,
            pdf_s3_key=None,
            magic_pages=None,
            url_cards=None,
            image_cards=image_cards,
        )


def test_teacher_can_create_image_upload_url(repo):
    result = create_week_image_upload(
        repo,
        actor_username="teacher01",
        week_id="week-001",
        filename="課堂 白板.PNG",
        content_type="image/png",
        upload_url_factory=lambda key, content_type: f"https://upload.example/{key}?type={content_type}",
    )

    assert result["image_key"].startswith("images/week-001/")
    assert result["image_key"].endswith("-課堂-白板.png")
    assert result["content_type"] == "image/png"
    assert result["upload_url"] == f"https://upload.example/{result['image_key']}?type=image/png"


@pytest.mark.parametrize("content_type", ["image/gif", "application/pdf", ""])
def test_image_upload_rejects_unsupported_content_type(repo, content_type):
    with pytest.raises(BadRequest, match="unsupported image type"):
        create_week_image_upload(
            repo,
            actor_username="teacher01",
            week_id="week-001",
            filename="board.gif",
            content_type=content_type,
            upload_url_factory=lambda key, content_type: "https://upload.example",
        )
