from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_repo(path: str) -> str:
    return (ROOT / path).read_text()


def test_teacher_frontend_edits_url_cards_and_scopes_weeks_by_class():
    main_ts = read_repo("frontend/src/main.ts")

    assert "editingUrlCardIndex" in main_ts
    assert "data-edit-url-card" in main_ts
    assert "取消編輯" in main_ts
    assert "teacher-class-selector" in main_ts
    assert "class_id" in main_ts
    assert "selectedTeacherClass" in main_ts


def test_teacher_frontend_hard_deletes_selected_week_from_select_option():
    main_ts = read_repo("frontend/src/main.ts")

    assert "deleteSelectedWeek" in main_ts
    assert "data-delete-week" in main_ts
    assert "showConfirmModal" in main_ts
    assert "const selectedWeek = selectedTeacherWeek()" in main_ts
    assert "method: 'DELETE'" in main_ts
    assert "`/teacher/weeks/${selectedWeek.week_id}`" in main_ts
    assert "teacherWeeks.find((week) => week.week_id === value('#week-number'))" in main_ts


def test_teacher_home_uses_selected_class_scoped_week_list():
    main_ts = read_repo("frontend/src/main.ts")
    render_home = main_ts[
        main_ts.index("async function renderHome"):main_ts.index("async function renderWeek")
    ]

    assert "`/teacher/classes/${selectedTeacherClass}/weeks`" in render_home
    assert "apiFetch<WeekSummary[]>('/teacher/weeks', token)" not in render_home
    assert "teacher-home-class-selector" in render_home
    assert "renderHome()" in render_home


def test_student_week_route_returns_class_weeks_not_full_table():
    routes_student = read_repo("backend/magic_api/routes_student.py")

    assert "weeks_visible_for_student_classes" in routes_student
    assert '"is_open": week.week_id in opened' in routes_student
    assert "if week.class_id == class_id" in routes_student


def test_student_home_has_class_switcher_for_multi_class_students():
    main_ts = read_repo("frontend/src/main.ts")
    app_py = read_repo("backend/magic_api/app.py")
    render_home = main_ts[
        main_ts.index("async function renderHome"):main_ts.index("async function renderWeek")
    ]

    assert "student-home-class-selector" in render_home
    assert "studentClassIds(me)" in render_home
    assert "`/student/classes/${selectedStudentClass}/weeks`" in render_home
    assert 'segments[0] == "student"' in app_py
    assert 'segments[1] == "classes"' in app_py


def test_lambda_terraform_wires_live_cognito_admin_sync():
    lambda_tf = read_repo("infra/lambda.tf")

    assert "COGNITO_USER_POOL_ID" in lambda_tf
    assert "dynamodb:DeleteItem" in lambda_tf
    assert "cognito-idp:AdminGetUser" in lambda_tf


def test_terraform_seeds_initial_admin_app_profile():
    dynamodb_tf = read_repo("infra/dynamodb.tf")

    assert 'resource "aws_dynamodb_table_item" "initial_admin_profile"' in dynamodb_tf
    assert "var.initial_admin_username" in dynamodb_tf
    assert "role" in dynamodb_tf and '"admin"' in dynamodb_tf
    assert "status" in dynamodb_tf and '"active"' in dynamodb_tf
    assert "identity_sync_status" in dynamodb_tf and '"synced"' in dynamodb_tf


def test_terraform_can_optionally_seed_second_cognito_admin():
    cognito_tf = read_repo("infra/cognito.tf")
    dynamodb_tf = read_repo("infra/dynamodb.tf")
    variables_tf = read_repo("infra/variables.tf")
    locals_tf = read_repo("infra/locals.tf")
    tfvars_example = read_repo("infra/terraform.tfvars.example")

    assert "second_admin_requested" in locals_tf
    assert 'variable "second_admin_username"' in variables_tf
    assert 'variable "second_admin_email"' in variables_tf
    assert 'variable "second_admin_temp_password"' in variables_tf
    assert 'resource "aws_cognito_user" "second_admin"' in cognito_tf
    assert 'resource "aws_cognito_user_in_group" "second_admin"' in cognito_tf
    assert "local.second_admin_requested ? 1 : 0" in cognito_tf
    assert "must all be set together" in cognito_tf
    assert 'group_name   = aws_cognito_user_group.groups["admin"].name' in cognito_tf
    assert 'resource "aws_dynamodb_table_item" "second_admin_profile"' in dynamodb_tf
    assert "var.second_admin_username" in dynamodb_tf
    assert "second_admin_username" in tfvars_example
    assert "second_admin_email" in tfvars_example
    assert "second_admin_temp_password" in tfvars_example


def test_required_architecture_review_artifact_is_persisted():
    report = ROOT / "infra/architecture-review.md"

    assert report.exists()
    text = report.read_text()
    assert "AWS Well-Architected IaC Review" in text
    assert "| High | 0 |" in text


def test_infra_defines_operational_alarms():
    alarms_tf = read_repo("infra/alarms.tf")

    assert 'resource "aws_sns_topic" "alerts"' in alarms_tf
    assert 'resource "aws_sns_topic_subscription" "alerts_email"' in alarms_tf
    assert 'resource "aws_cloudwatch_metric_alarm" "lambda_errors"' in alarms_tf
    assert 'resource "aws_cloudwatch_metric_alarm" "api_5xx"' in alarms_tf
    assert "alarm_actions" in alarms_tf
    assert "ok_actions" in alarms_tf


def test_api_logging_is_error_only_not_all_request_access_logs():
    alarms_tf = read_repo("infra/alarms.tf")
    api_gateway_tf = read_repo("infra/api_gateway.tf")
    app_py = read_repo("backend/magic_api/app.py")

    assert 'resource "aws_cloudwatch_log_group" "api_gateway_access"' not in alarms_tf
    assert 'access_log_settings {' not in api_gateway_tf
    assert '"event": "api_error"' in app_py
    assert '"event": "unexpected_error"' in app_py
    assert '"status_code": error.status_code' in app_py
    assert '"error": error.code' in app_py


def test_production_lite_infra_enables_data_protection_guardrails():
    dynamodb_tf = read_repo("infra/dynamodb.tf")
    s3_tf = read_repo("infra/s3.tf")
    variables_tf = read_repo("infra/variables.tf")

    assert dynamodb_tf.count("point_in_time_recovery") == 3
    assert dynamodb_tf.count("enabled = true") >= 3
    assert s3_tf.count('resource "aws_s3_bucket_versioning"') == 3
    assert s3_tf.count('status = "Enabled"') == 3
    assert 'default     = true' in variables_tf


def test_terraform_protects_critical_services_from_accidental_destroy():
    acm_tf = read_repo("infra/acm.tf")
    api_gateway_tf = read_repo("infra/api_gateway.tf")
    cloudfront_tf = read_repo("infra/cloudfront.tf")
    cognito_tf = read_repo("infra/cognito.tf")
    dynamodb_tf = read_repo("infra/dynamodb.tf")
    lambda_tf = read_repo("infra/lambda.tf")
    s3_tf = read_repo("infra/s3.tf")
    variables_tf = read_repo("infra/variables.tf")

    def assignment_count(terraform_source: str, name: str, value: str) -> int:
        return sum(
            1
            for line in terraform_source.splitlines()
            if " ".join(line.split()) == f"{name} = {value}"
        )

    assert "critical identity/data service deletion protection" in variables_tf

    assert (
        assignment_count(
            cognito_tf,
            "deletion_protection",
            'var.protect_identity_data ? "ACTIVE" : "INACTIVE"',
        )
        == 1
    )
    assert assignment_count(cognito_tf, "prevent_destroy", "true") >= 1

    assert (
        assignment_count(
            dynamodb_tf,
            "deletion_protection_enabled",
            "var.protect_identity_data",
        )
        == 3
    )
    assert assignment_count(dynamodb_tf, "prevent_destroy", "true") == 3

    assert assignment_count(s3_tf, "force_destroy", "!var.protect_identity_data") == 3
    assert assignment_count(s3_tf, "prevent_destroy", "true") == 3

    assert assignment_count(cloudfront_tf, "retain_on_delete", "var.protect_identity_data") == 2
    assert assignment_count(cloudfront_tf, "prevent_destroy", "true") == 2

    assert assignment_count(api_gateway_tf, "prevent_destroy", "true") >= 1
    assert assignment_count(lambda_tf, "prevent_destroy", "true") >= 2
    assert assignment_count(acm_tf, "prevent_destroy", "true") >= 1


def test_production_lite_infra_defines_budget_notifications():
    budget_tf = read_repo("infra/budgets.tf")
    variables_tf = read_repo("infra/variables.tf")
    tfvars_example = read_repo("infra/terraform.tfvars.example")

    assert 'resource "aws_budgets_budget" "monthly"' in budget_tf
    assert 'budget_type  = "COST"' in budget_tf
    assert 'limit_unit   = "USD"' in budget_tf
    assert "threshold_type" in budget_tf and "ABSOLUTE_VALUE" in budget_tf
    assert 'threshold                  = 10' in budget_tf
    assert 'threshold                  = 20' in budget_tf
    assert 'threshold                  = 50' in budget_tf
    assert 'cost_filter {' in budget_tf
    assert "name" in budget_tf and "TagKeyValue" in budget_tf
    assert "user:magic$true" in budget_tf
    assert 'resource "aws_ce_cost_allocation_tag" "magic"' in budget_tf
    assert 'tag_key = "magic"' in budget_tf
    assert 'status  = "Active"' in budget_tf
    assert 'subscriber_email_addresses = [var.initial_admin_email]' in budget_tf
    assert 'variable "monthly_budget_limit_usd"' in variables_tf
    assert 'monthly_budget_limit_usd = "50"' in tfvars_example


def test_static_deploy_builds_with_terraform_config_and_keeps_magic_pages_private():
    deploy = read_repo("scripts/deploy-static.sh")

    assert 'export VITE_API_BASE_URL="${VITE_API_BASE_URL:-$(TF_OUTPUT api_gateway_url)}"' in deploy
    user_pool_fallback = (
        'export VITE_COGNITO_USER_POOL_ID="'
        '${VITE_COGNITO_USER_POOL_ID:-$(TF_OUTPUT cognito_user_pool_id)}"'
    )
    client_fallback = (
        'export VITE_COGNITO_CLIENT_ID="'
        '${VITE_COGNITO_CLIENT_ID:-$(TF_OUTPUT cognito_user_pool_client_id)}"'
    )
    assert user_pool_fallback in deploy
    assert client_fallback in deploy
    assert "CONTENT_BUCKET" in deploy
    assert '--exclude "magic-pages/*"' in deploy
    assert 's3://$CONTENT_BUCKET/magic-pages/' in deploy


def test_api_gateway_defines_unauthenticated_options_routes_for_cors_preflight():
    api_gateway_tf = read_repo("infra/api_gateway.tf")

    assert 'allow_methods = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]' in api_gateway_tf
    assert 'route_key          = "OPTIONS /{proxy+}"' in api_gateway_tf
    assert 'route_key          = "OPTIONS /"' in api_gateway_tf
    assert api_gateway_tf.count('authorization_type = "NONE"') >= 2


def test_frontend_opens_material_cards_in_new_tabs_instead_of_iframe_embedding():
    main_ts = read_repo("frontend/src/main.ts")

    assert "escapeHtml" in main_ts
    assert "function formatDisplayName(name: unknown): string" in main_ts
    assert "magic_page_urls" in main_ts
    assert 'id="content-frame"' not in main_ts
    assert "content-card" in main_ts
    assert "openMaterialCard" in main_ts
    assert "window.open(url, '_blank', 'noopener')" in main_ts
    assert "target=\"_blank\"" in main_ts
    assert 'class="pdf"' not in main_ts
    assert 'href="/magic-pages/${page}"' not in main_ts


def test_pdf_key_is_server_constrained_to_content_pdf_prefix():
    main_ts = read_repo("frontend/src/main.ts")
    routes_teacher = read_repo("backend/magic_api/routes_teacher.py")

    assert 'id="pdf-key"' not in main_ts
    assert 'expected_pdf_key = f"pdf/{week.week_id}.pdf"' not in routes_teacher
    assert 'pdf_s3_key.startswith("pdf/")' in routes_teacher
    assert "pdf_s3_key must be a PDF under pdf/" in routes_teacher


def test_admin_ui_uses_operable_tables_and_choices_instead_of_json_or_csv():
    admin_ts = read_repo("frontend/src/admin.ts")
    styles = read_repo("frontend/src/styles.css")

    assert 'id="status"' in admin_ts
    assert "temporary_password" in admin_ts
    assert "generateTemporaryPassword" in admin_ts
    assert "產生臨時密碼" in admin_ts
    assert "<table" in admin_ts
    assert "JSON.stringify(users" not in admin_ts
    assert "<pre>" not in admin_ts
    assert 'type="checkbox"' in admin_ts
    assert "id: 'jul'" in admin_ts
    assert "id: 'aug'" in admin_ts
    assert "Classes CSV" not in admin_ts
    assert "Open Week IDs CSV" not in admin_ts
    assert "/admin/users/password-reset" in admin_ts
    assert "/sync-identity" in admin_ts
    assert "resetAndSyncUser" in admin_ts
    assert "function formatDisplayName(name: unknown): string" in admin_ts
    assert "/device/reset" in admin_ts
    assert "resetSelectedStudentDevice" in admin_ts
    assert ".cell-actions" in styles
    assert ".admin-table td:last-child {\n  display: flex;" not in styles


def test_admin_and_teacher_management_use_dashboard_layouts_not_stacked_cards():
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "admin-dashboard" in admin_ts
    assert "dashboard-rail" in admin_ts
    assert "dashboard-rail-button" in admin_ts
    assert "dashboard-canvas" in admin_ts
    assert "dashboard-canvas-panel" in admin_ts
    assert "activateDashboardPanel" in admin_ts
    assert "management-dashboard" in main_ts
    assert "dashboard-rail" in main_ts
    assert "dashboard-rail-button" in main_ts
    assert "dashboard-canvas" in main_ts
    assert "dashboard-canvas-panel" in main_ts
    assert "activateDashboardPanel" in main_ts
    assert ".dashboard-shell" in styles
    assert ".dashboard-rail" in styles
    assert ".dashboard-rail-button" in styles
    assert ".dashboard-canvas" in styles
    assert ".dashboard-canvas-panel" in styles


def test_dashboard_canvases_switch_from_left_buttons_and_scale_responsively():
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    for source in [admin_ts, main_ts]:
        assert "data-dashboard-target" in source
        assert "data-dashboard-panel" in source
        assert "aria-selected" in source
        assert "hidden" in source

    assert "grid-template-columns: clamp(112px, 12vw, 148px) minmax(0, 1fr);" in styles
    assert "min-height: min(760px, calc(100vh - 120px));" in styles
    assert "@media (max-width: 900px)" in styles
    assert "grid-template-columns: 1fr;" in styles
    assert "overflow-x: auto" in styles


def test_dashboard_rail_keeps_original_palette_text_labels_and_no_logo():
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "dashboard-logo" not in admin_ts
    assert "dashboard-logo" not in main_ts
    assert "dashboard-logo" not in styles
    for emoji in ["👤", "📱", "📋", "📅", "🪄", "👁", "📚"]:
        assert emoji not in admin_ts
        assert emoji not in main_ts

    assert "帳號維護" in admin_ts
    assert "裝置授權" in admin_ts
    assert "使用者清單" in admin_ts
    assert "班級週次" in admin_ts
    assert "週內容" in main_ts
    assert "班級可見週次" in main_ts
    assert "目前 Weeks" in main_ts
    assert "border-radius: 18px;" in styles
    assert "border-radius: 50%;" not in styles
    assert "linear-gradient" not in styles
    assert "color: #101010" not in styles


def test_dashboard_summary_hides_teacher_material_counts_and_admin_shows_role_counts():
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")

    assert "teacherCount" in admin_ts
    assert "studentCount" in admin_ts
    assert "位老師" in admin_ts
    assert "位學生" in admin_ts
    assert "${users.length} users" not in admin_ts
    assert "${weeks.length} weeks" not in admin_ts

    assert "${teacherWeeks.length} weeks" not in main_ts
    assert "${teacherAssets.magic_pages.length} materials" not in main_ts


def test_week_material_cards_are_compact_enough_for_page_overview():
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "compact-material-grid" in main_ts
    assert "material-card-grid" in main_ts
    assert "aspect-ratio: 1 / 1" not in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert "height: 160px" in styles
    assert "max-height" not in styles


def test_vite_dev_server_defines_browser_global_for_cognito_dependency():
    vite_config = read_repo("frontend/vite.config.ts")

    assert "define:" in vite_config
    assert "'global': 'globalThis'" in vite_config


def test_frontend_auth_does_not_throw_before_render_when_runtime_config_is_missing():
    auth_ts = read_repo("frontend/src/auth.ts")

    assert "const pool = new CognitoUserPool" not in auth_ts
    assert "function getUserPool(): CognitoUserPool" in auth_ts
    assert "if (!hasCognitoConfig()) return Promise.resolve(null);" in auth_ts


def test_frontend_api_calls_refresh_cognito_session_before_requesting_backend():
    api_ts = read_repo("frontend/src/api.ts")
    main_ts = read_repo("frontend/src/main.ts")
    admin_ts = read_repo("frontend/src/admin.ts")

    assert "class ApiFetchError extends Error" in api_ts
    assert "readonly status: number" in api_ts
    assert "throw new ApiFetchError" in api_ts

    for source in [main_ts, admin_ts]:
        assert "class SessionExpiredError extends Error" in source
        assert "async function apiFetchWithSession<T>" in source
        assert "const freshToken = await getCurrentToken();" in source
        assert "token = freshToken;" in source
        assert "error instanceof ApiFetchError && error.status === 401" in source
        assert "登入已逾時，請重新登入。" in source

    main_render_home = main_ts[
        main_ts.index("async function renderHome"):main_ts.index("async function renderWeek")
    ]
    assert "apiFetchWithSession<Me>('/me')" in main_render_home
    assert "apiFetch<Me>('/me', token)" not in main_render_home
    assert "addEventListener('click', () => { void renderHome().catch(showError); })" in main_ts
    assert ".catch(showError)" in admin_ts


def test_login_and_first_password_change_submit_on_enter_key():
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")

    for source in [admin_ts, main_ts]:
        assert 'id="login-form"' in source
        assert 'id="change-password-form"' in source
        assert "addEventListener('submit'" in source
        assert "event.preventDefault()" in source
        assert 'button id="login" type="submit"' in source
        assert 'button id="change" type="submit"' in source


def test_login_transitions_show_loading_buffer_before_main_api_render():
    loading_ts = read_repo("frontend/src/loading.ts")
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "function renderLoading" in loading_ts
    assert "app-loading-card" in loading_ts
    assert "登入中" in admin_ts
    assert "登入中" in main_ts
    for source in [admin_ts, main_ts]:
        assert "import { renderLoading } from './loading';" in source
        assert source.count("renderLoading(") >= 2
        assert "const username = value('#username');" in source
        assert "const password = value('#password');" in source
        assert "await login(username, password)" in source
        assert "const newPassword = value('#new-password');" in source
        assert "await completeNewPassword(challengeUser, newPassword)" in source
        assert source.index("const username = value('#username');") < source.index("renderLoading(")

    assert ".app-loading-card" in styles
    assert ".app-loading-dot" in styles
    assert "animation: app-loading-pulse" in styles


def test_password_inputs_have_show_password_toggles_without_submitting_forms():
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    for source in [admin_ts, main_ts]:
        assert "function bindPasswordToggles(): void" in source
        assert 'class="password-field"' in source
        assert 'data-password-toggle="password"' in source
        assert 'data-password-toggle="new-password"' in source
        assert 'type="button"' in source
        assert "input.type = input.type === 'password' ? 'text' : 'password';" in source
        assert "button.textContent = input.type === 'password' ? '顯示密碼' : '隱藏密碼';" in source

    assert ".password-field" in styles
    assert ".password-field button" in styles


def test_teacher_ui_uses_magic_page_s3_content_choices_instead_of_pdf_upload_or_filename_csv():
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "/teacher/dashboard" in main_ts
    assert "/teacher/content-assets" not in main_ts
    assert 'id="week-number"' in main_ts
    assert "<select id=\"week-number\"" in main_ts
    assert 'id="pdf-key"' not in main_ts
    assert "data-pdf-url" not in main_ts
    assert 'id="pdf-preview"' not in main_ts
    assert "HTML PDF 預覽" not in main_ts
    assert "S3 Magic page 物件" not in main_ts
    assert "S3 content bucket" not in main_ts
    assert "magic-pages/*.html" not in main_ts
    assert 'id="week-title"' in main_ts
    assert "readonly" not in main_ts
    assert "週主題名稱" in main_ts
    assert 'id="url-card-name"' in main_ts
    assert 'id="url-card-url"' in main_ts
    assert "add-url-card" in main_ts
    assert "url_cards" in main_ts
    assert 'id="image-card-file"' in main_ts
    assert 'accept="image/jpeg,image/png,image/webp"' in main_ts
    assert 'id="magic-pages"' not in main_ts
    assert "magic-page-choice" in main_ts
    assert "pdf_upload_url" not in main_ts
    assert "PDF from S3 content" not in main_ts
    assert "pdf_s3_key" not in main_ts
    assert "@media" in styles


def test_teacher_save_actions_show_modal_success_feedback():
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "function showMessage(message: string): void" in main_ts
    assert "showResponseModal(message" in main_ts
    assert "await renderTeacherPanel();" in main_ts
    assert "showMessage('週主題與教材已儲存。');" in main_ts
    assert "showMessage('班級可見週次已儲存。');" in main_ts
    assert "max-width: 768px" in styles
    assert "external-content-panel" in styles
    assert "url-card-list" in styles


def test_material_ui_hides_service_names_extensions_and_raw_urls():
    main_ts = read_repo("frontend/src/main.ts")

    assert "教材不在頁面內嵌顯示" not in main_ts
    assert "S3 HTML 教材" not in main_ts
    assert "S3 Magic page" not in main_ts
    assert "外部連結" not in main_ts
    assert "URL Card" not in main_ts
    assert "新增 URL" not in main_ts
    assert "請輸入 URL" not in main_ts
    assert "URL 必須" not in main_ts
    assert "請至少選擇 S3 HTML" not in main_ts
    assert "<small>${escapeHtml(card.url)}</small>" not in main_ts
    assert "kind:" not in main_ts


def test_frontend_visible_copy_avoids_identity_provider_branding():
    admin_ts = read_repo("frontend/src/admin.ts")
    auth_ts = read_repo("frontend/src/auth.ts")

    assert "<th>Cognito</th>" not in admin_ts
    assert "Frontend Cognito config is missing" not in auth_ts


def test_teacher_ui_includes_class_week_visibility_controls():
    main_ts = read_repo("frontend/src/main.ts")

    assert "CLASSES" in main_ts
    assert "/teacher/classes/${classId}/open-weeks" in main_ts
    assert "renderTeacherClassAccessEditor" in main_ts
    assert "saveTeacherClassAccess" in main_ts
    assert "教師決定各班可見週次" in main_ts


def test_admin_entry_is_also_registered_as_pwa_shell():
    admin_html = read_repo("frontend/admin.html")
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")
    pwa_ts = read_repo("frontend/src/pwa.ts")
    sw_js = read_repo("frontend/public/sw.js")

    assert '<link rel="manifest" href="/manifest.webmanifest" />' in admin_html
    assert "registerAppServiceWorker" in admin_ts
    assert "registerAppServiceWorker" in main_ts
    assert "navigator.serviceWorker.register('/sw.js')" in pwa_ts
    assert "controllerchange" in pwa_ts
    assert "window.location.reload()" in pwa_ts
    assert "SKIP_WAITING" in pwa_ts
    assert "magic-app-shell-v2" in sw_js
    assert "self.skipWaiting()" in sw_js
    assert "self.clients.claim()" in sw_js


def test_cloudfront_distribution_ids_are_output_for_cache_invalidation():
    outputs_tf = read_repo("infra/outputs.tf")

    assert 'output "app_cloudfront_distribution_id"' in outputs_tf
    assert 'output "admin_cloudfront_distribution_id"' in outputs_tf


def test_cloud_maintenance_runbook_documents_service_backup_ownership():
    runbook = read_repo("docs/cloud-maintenance.md")

    assert "Magic Cloud 維護書" in runbook
    assert "prod v1.0" in runbook
    assert "備份與保留政策" in runbook
    assert "DynamoDB" in runbook and "PITR" in runbook
    assert "S3" in runbook and "Versioning" in runbook
    assert "Cognito" in runbook and "deletion protection" in runbook
    assert "CloudWatch" in runbook and "14 天" in runbook
    assert "AWS Budgets" in runbook
    assert "Terraform state" in runbook
    assert "每週一" in runbook
    assert "事故 Runbook" in runbook


def test_aws_architecture_guardrails_use_aws_icons_and_do_not_overlap_core_diagram():
    diagram = ROOT / "docs/architecture/aws -architecture.drawio"
    tree = ET.parse(diagram)
    root = tree.getroot()

    required_icon_fragments = {
        "cloudwatch_error_logs": "mxgraph.aws4.cloudwatch",
        "cloudwatch_alarms": "mxgraph.aws4.cloudwatch",
        "sns_email_alerts": "mxgraph.aws4.sns",
        "aws_budget_magic_tag": "mxgraph.aws4.budgets",
    }

    cells = {cell.attrib["id"]: cell for cell in root.findall(".//mxCell[@id]")}
    for cell_id, icon_fragment in required_icon_fragments.items():
        style = cells[cell_id].attrib["style"]
        assert "shape=mxgraph.aws4.productIcon" in style
        assert f"prIcon={icon_fragment}" in style

    guardrails = cells["prod_guardrails_group"].find("mxGeometry").attrib
    aws_cloud = cells["aws_cloud"].find("mxGeometry").attrib
    assert float(guardrails["y"]) >= 850
    assert float(aws_cloud["height"]) >= 1080

    ignored_container_ids = {
        "aws_cloud",
        "prod_guardrails_group",
        "YUsTrCKgYxTvA2nvYZWJ-24",
    }
    parent_by_id = {
        cell.attrib["id"]: cell.attrib.get("parent")
        for cell in root.findall(".//mxCell[@id]")
    }

    def absolute_origin(cell_id: str) -> tuple[float, float]:
        cell = cells[cell_id]
        geometry = cell.find("mxGeometry")
        x = float(geometry.attrib.get("x", 0)) if geometry is not None else 0
        y = float(geometry.attrib.get("y", 0)) if geometry is not None else 0
        parent_id = parent_by_id.get(cell_id)
        if parent_id in cells:
            parent_x, parent_y = absolute_origin(parent_id)
            return x + parent_x, y + parent_y
        return x, y

    boxes = []
    for cell in root.findall(".//mxCell[@vertex='1']"):
        cell_id = cell.attrib["id"]
        if cell_id in ignored_container_ids:
            continue
        geometry = cell.find("mxGeometry")
        if geometry is None:
            continue
        x, y = absolute_origin(cell_id)
        attrs = geometry.attrib
        boxes.append(
            (
                cell_id,
                x,
                y,
                float(attrs.get("width", 0)),
                float(attrs.get("height", 0)),
            )
        )

    overlaps = []
    for index, (left_id, left_x, left_y, left_w, left_h) in enumerate(boxes):
        for right_id, right_x, right_y, right_w, right_h in boxes[index + 1 :]:
            if (
                left_x < right_x + right_w
                and left_x + left_w > right_x
                and left_y < right_y + right_h
                and left_y + left_h > right_y
            ):
                overlaps.append((left_id, right_id))

    assert overlaps == []


def test_aws_architecture_service_labels_are_below_icons_and_routes_avoid_icons():
    diagram = ROOT / "docs/architecture/aws -architecture.drawio"
    root = ET.parse(diagram).getroot()
    cells = {cell.attrib["id"]: cell for cell in root.findall(".//mxCell[@id]")}
    parent_by_id = {
        cell.attrib["id"]: cell.attrib.get("parent")
        for cell in root.findall(".//mxCell[@id]")
    }

    def absolute_box(cell_id: str) -> tuple[float, float, float, float]:
        cell = cells[cell_id]
        geometry = cell.find("mxGeometry")
        assert geometry is not None
        x = float(geometry.attrib.get("x", 0))
        y = float(geometry.attrib.get("y", 0))
        parent_id = parent_by_id.get(cell_id)
        while parent_id in cells:
            parent = cells[parent_id]
            parent_geometry = parent.find("mxGeometry")
            if parent_geometry is not None:
                x += float(parent_geometry.attrib.get("x", 0))
                y += float(parent_geometry.attrib.get("y", 0))
            parent_id = parent_by_id.get(parent_id)
        return (
            x,
            y,
            float(geometry.attrib.get("width", 0)),
            float(geometry.attrib.get("height", 0)),
        )

    service_icon_ids = {
        cell.attrib["id"]
        for cell in root.findall(".//mxCell[@vertex='1']")
        if "shape=mxgraph.aws4.productIcon" in cell.attrib.get("style", "")
    }
    service_boxes = {cell_id: absolute_box(cell_id) for cell_id in service_icon_ids}

    for cell_id in service_icon_ids:
        style = cells[cell_id].attrib["style"]
        assert "verticalLabelPosition=bottom" in style
        assert "verticalAlign=top" in style

    def segment_intersects_box(
        start: tuple[float, float],
        end: tuple[float, float],
        box: tuple[float, float, float, float],
        padding: float = 4,
    ) -> bool:
        x, y, width, height = box
        x1, y1 = start
        x2, y2 = end
        left, right = x - padding, x + width + padding
        top, bottom = y - padding, y + height + padding
        if x1 == x2:
            if not (left <= x1 <= right):
                return False
            return max(y1, y2) >= top and min(y1, y2) <= bottom
        if y1 == y2:
            if not (top <= y1 <= bottom):
                return False
            return max(x1, x2) >= left and min(x1, x2) <= right
        return False

    route_overlaps = []
    for edge in root.findall(".//mxCell[@edge='1']"):
        source_id = edge.attrib.get("source")
        target_id = edge.attrib.get("target")
        if source_id not in cells or target_id not in cells:
            continue
        source_x, source_y, source_w, source_h = absolute_box(source_id)
        target_x, target_y, target_w, target_h = absolute_box(target_id)
        points = [(source_x + source_w / 2, source_y + source_h / 2)]
        geometry = edge.find("mxGeometry")
        if geometry is not None:
            for point in geometry.findall("./Array/mxPoint"):
                points.append((float(point.attrib["x"]), float(point.attrib["y"])))
        points.append((target_x + target_w / 2, target_y + target_h / 2))

        for start, end in zip(points, points[1:], strict=False):
            for icon_id, box in service_boxes.items():
                if icon_id in {source_id, target_id}:
                    continue
                if segment_intersects_box(start, end, box):
                    route_overlaps.append((edge.attrib["id"], icon_id))

    assert route_overlaps == []


def test_static_deploy_invalidates_public_magic_page_cache():
    deploy = read_repo("scripts/deploy-static.sh")

    assert "APP_DISTRIBUTION_ID" in deploy
    assert "ADMIN_DISTRIBUTION_ID" in deploy
    assert 'Invalidating %s CloudFront distribution: %s' in deploy
    assert 'INVALIDATE_DISTRIBUTION "app" "$APP_DISTRIBUTION_ID"' in deploy
    assert 'INVALIDATE_DISTRIBUTION "admin" "$ADMIN_DISTRIBUTION_ID"' in deploy
    assert "create-invalidation" in deploy
    assert "wait invalidation-completed" in deploy
    assert '--paths "/*"' in deploy


def test_public_snapshot_does_not_include_github_actions_workflow():
    assert not (ROOT / ".github/workflows/deploy-static.yml").exists()


def test_smoke_test_rejects_public_magic_page_content():
    smoke = read_repo("scripts/smoke-test.sh")

    assert "/magic-pages/mindreading.html" in smoke
    assert "心靈感應" in smoke
    assert "still serves public magic page content" in smoke


def test_release_checklist_documents_production_lite_sequence():
    checklist = read_repo("docs/release-checklist.md")

    assert "Production-lite release checklist" in checklist
    assert "backend/.venv/bin/pytest -q" in checklist
    assert "backend/.venv/bin/ruff check backend" in checklist
    assert "npm run build" in checklist
    assert "terraform plan" in checklist
    assert "terraform apply" in checklist
    assert "./scripts/deploy-static.sh" in checklist
    assert "./scripts/smoke-test.sh" in checklist
    assert "DynamoDB Point-in-Time Recovery" in checklist
    assert "S3 versioning" in checklist
    assert "AWS Budget" in checklist


def test_admin_ui_supports_student_device_reset_and_user_deletion():
    admin_ts = read_repo("frontend/src/admin.ts")

    assert 'id="reset-device-student"' in admin_ts
    assert "studentOptions" in admin_ts
    assert "/device/reset" in admin_ts
    assert "resetSelectedStudentDevice" in admin_ts
    assert "data-delete-user" in admin_ts
    assert "deleteUser" in admin_ts
    assert "DELETE" in admin_ts
    assert "showConfirmModal" in admin_ts
    assert "confirm(" not in admin_ts


def test_frontend_responses_use_shared_modal_instead_of_inline_red_text():
    modal_ts = read_repo("frontend/src/modal.ts")
    admin_ts = read_repo("frontend/src/admin.ts")
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "showResponseModal" in modal_ts
    assert "showConfirmModal" in modal_ts
    assert "role=\"dialog\"" in modal_ts
    assert "app-modal-backdrop" in modal_ts
    assert "app-modal-card" in modal_ts
    assert "app-modal-actions" in modal_ts
    assert "showResponseModal" in admin_ts
    assert "showResponseModal" in main_ts
    assert "querySelector('.error')" not in admin_ts
    assert "querySelector('.error')" not in main_ts
    assert "textContent = error instanceof Error" not in admin_ts
    assert "textContent = error instanceof Error" not in main_ts
    assert ".app-modal-backdrop" in styles
    assert ".app-modal-card" in styles
    assert "background: var(--bg-card);" in styles
    assert ".app-modal-actions button" in styles


def test_week_material_cards_use_compact_overview_layout():
    styles = read_repo("frontend/src/styles.css")

    assert "material-card-grid" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert "height: 160px" in styles
    assert "aspect-ratio: 1 / 1;" not in styles


def test_teacher_frontend_uploads_and_saves_image_cards():
    main_ts = read_repo("frontend/src/main.ts")
    styles = read_repo("frontend/src/styles.css")

    assert "editingImageCards" in main_ts
    assert "image-card-file" in main_ts
    assert 'accept="image/jpeg,image/png,image/webp"' in main_ts
    assert "`/teacher/weeks/${targetWeekId}/image-upload`" in main_ts
    assert "method: 'PUT'" in main_ts
    assert "image_cards: editingImageCards.map" in main_ts
    assert "image-material-card" in main_ts
    assert "object-fit: contain" in styles


def test_backend_defines_teacher_image_upload_route_and_dynamic_content_type():
    app_py = read_repo("backend/magic_api/app.py")
    signing_py = read_repo("backend/magic_api/s3_signing.py")

    assert 'segments[3] == "image-upload"' in app_py
    assert "_IMAGE_UPLOAD_URL_FACTORY" in app_py
    assert "content_type=content_type" in app_py
    assert 'ContentType": content_type' in signing_py
