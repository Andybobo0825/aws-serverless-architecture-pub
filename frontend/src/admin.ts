import './styles.css';
import { ApiFetchError, apiFetch } from './api';
import { completeNewPassword, getCurrentToken, login, logout } from './auth';
import { showConfirmModal, showResponseModal } from './modal';
import { registerAppServiceWorker } from './pwa';
import { renderLoading } from './loading';

const root = document.querySelector<HTMLDivElement>('#admin');
if (!root) throw new Error('missing #admin');
let token: string | null = null;

type Role = 'student' | 'teacher' | 'admin';
type Status = 'active' | 'inactive';
type ClassId = 'jul' | 'aug';

interface UserProfile {
  username: string;
  role: Role;
  status: Status;
  classes: ClassId[];
  device_id?: string | null;
  identity_sync_status?: string | null;
  identity_sync_error?: string | null;
}

interface WeekSummary {
  week_id: string;
  week_number: number;
  title: string;
}

interface ClassAccess {
  class_id: ClassId;
  open_week_ids: string[];
}

interface AdminDashboard {
  users: UserProfile[];
  weeks: WeekSummary[];
  class_access: ClassAccess[];
}

const CLASSES: Array<{ id: ClassId; label: string }> = [
  { id: 'jul', label: '7月班' },
  { id: 'aug', label: '8月班' }
];

function escapeHtml(value: unknown): string {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[char]!));
}

function formatDisplayName(name: unknown): string {
  return String(name ?? '').replace(/\.html$/i, '');
}

function setHtml(html: string): void { root!.innerHTML = html; }
class SessionExpiredError extends Error {
  constructor() {
    super('登入已逾時，請重新登入。');
    this.name = 'SessionExpiredError';
  }
}
function showError(error: unknown): void {
  if (error instanceof SessionExpiredError) return;
  void showResponseModal(error instanceof Error ? error.message : String(error), { title: '操作失敗' });
}
function showMessage(message: string): void {
  void showResponseModal(message, { title: '提示' });
}

function expireSession(): SessionExpiredError {
  token = null;
  logout();
  renderLogin();
  void showResponseModal('登入已逾時，請重新登入。', { title: '請重新登入' });
  return new SessionExpiredError();
}

async function apiFetchWithSession<T>(path: string, init: RequestInit = {}): Promise<T> {
  const freshToken = await getCurrentToken();
  if (!freshToken) throw expireSession();
  token = freshToken;
  try {
    return await apiFetch<T>(path, freshToken, init);
  } catch (error) {
    if (error instanceof ApiFetchError && error.status === 401) throw expireSession();
    throw error;
  }
}

function bindPasswordToggles(): void {
  document.querySelectorAll<HTMLButtonElement>('[data-password-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const targetId = button.dataset.passwordToggle;
      if (!targetId) return;
      const input = document.querySelector<HTMLInputElement>(`#${cssEscape(targetId)}`);
      if (!input) return;
      input.type = input.type === 'password' ? 'text' : 'password';
      button.textContent = input.type === 'password' ? '顯示密碼' : '隱藏密碼';
    });
  });
}

function generateTemporaryPassword(): string {
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  const numberPart = Array.from(bytes, (byte) => String(byte % 10)).join('');
  const upper = String.fromCharCode(65 + (bytes[0] % 26));
  const lower = String.fromCharCode(97 + (bytes[1] % 26));
  return `Magic${numberPart}${upper}${lower}`;
}

function renderLogin(): void {
  setHtml(`<form id="login-form" class="card"><h1>Admin Login</h1><label>Username <input id="username" autocomplete="username"></label><label>Password <span class="password-field"><input id="password" type="password" autocomplete="current-password"><button type="button" class="secondary" data-password-toggle="password">顯示密碼</button></span></label><button id="login" type="submit">登入</button></form>`);
  bindPasswordToggles();
  document.querySelector('#login-form')!.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const username = value('#username');
      const password = value('#password');
      renderLoading(root!, '登入中');
      const result = await login(username, password);
      if (result.requiredNewPassword && result.challengeUser) {
        renderChangePassword(result.challengeUser);
        return;
      }
      token = result.token ?? null;
      await renderAdmin();
    } catch (error) { renderLogin(); showError(error); }
  });
}

function renderChangePassword(challengeUser: Parameters<typeof completeNewPassword>[0]): void {
  setHtml(`<form id="change-password-form" class="card"><h1>首次登入改密碼</h1><label>New password <span class="password-field"><input id="new-password" type="password"><button type="button" class="secondary" data-password-toggle="new-password">顯示密碼</button></span></label><button id="change" type="submit">更新密碼</button></form>`);
  bindPasswordToggles();
  document.querySelector('#change-password-form')!.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const newPassword = value('#new-password');
      renderLoading(root!, '登入中');
      token = await completeNewPassword(challengeUser, newPassword);
      await renderAdmin();
    } catch (error) { renderChangePassword(challengeUser); showError(error); }
  });
}

async function renderAdmin(): Promise<void> {
  if (!token) return renderLogin();
  const dashboard = await apiFetchWithSession<AdminDashboard>('/admin/dashboard');
  const { users, weeks } = dashboard;
  const classAccess = Object.fromEntries(dashboard.class_access.map((access) => [access.class_id, access.open_week_ids])) as Record<ClassId, string[]>;
  const teacherCount = users.filter((user) => user.role === 'teacher').length;
  const studentCount = users.filter((user) => user.role === 'student').length;

  setHtml(`
    <div class="toolbar"><h1>Admin Console</h1><button id="logout" class="secondary">登出</button></div>

    <section class="dashboard-shell admin-dashboard" aria-label="Admin dashboard">
      <aside class="dashboard-rail" aria-label="Admin function buttons">
        <button type="button" class="dashboard-rail-button active" data-dashboard-target="account-admin" aria-selected="true">帳號維護</button>
        <button type="button" class="dashboard-rail-button" data-dashboard-target="device-admin" aria-selected="false">裝置授權</button>
        <button type="button" class="dashboard-rail-button" data-dashboard-target="users-admin" aria-selected="false">使用者清單</button>
        <button type="button" class="dashboard-rail-button" data-dashboard-target="weeks-admin" aria-selected="false">班級週次</button>
      </aside>
      <div class="dashboard-canvas">
        <header class="dashboard-canvas-header">
          <div><p class="eyebrow">Admin Dashboard</p><h2 id="dashboard-title">帳號維護</h2></div>
          <div class="dashboard-summary">
            <span>${teacherCount} 位老師</span>
            <span>${studentCount} 位學生</span>
          </div>
        </header>
        <section id="account-admin" class="dashboard-canvas-panel" data-dashboard-panel="account-admin" data-dashboard-title="帳號維護">
          <h2>建立 / 更新帳號</h2>
          <div class="form-grid">
            <label>Username <input id="user-username" autocomplete="off" placeholder="student001"></label>
            <label>Role <select id="role"><option value="student">student</option><option value="teacher">teacher</option><option value="admin">admin</option></select></label>
            <label>Status <select id="status"><option value="active">active</option><option value="inactive">inactive</option></select></label>
            <label>Temporary password <input id="temporary-password" type="text" placeholder="至少10碼，含大小寫與數字"></label>
          </div>
          <div class="action-row"><button id="generate-temporary-password" type="button" class="secondary">產生臨時密碼</button><span class="hint">新帳號預設自動產生；編輯既有帳號時留空代表不重設密碼。</span></div>
          <fieldset class="choice-list">
            <legend>Classes</legend>
            ${classCheckboxes('user-class', [])}
          </fieldset>
          <div class="action-row"><button id="save-user">儲存帳號</button><button id="clear-user-form" class="secondary">清空</button></div>
        </section>

        <section id="device-admin" class="dashboard-canvas-panel" data-dashboard-panel="device-admin" data-dashboard-title="裝置授權" hidden>
          <h2>清除學員裝置授權</h2>
          <p class="muted">請先從下拉選單選擇學生，再按下清除；清除後該學生下次登入會重新綁定目前裝置。</p>
          <div class="form-grid">
            <label>Student <select id="reset-device-student">${studentOptions(users)}</select></label>
          </div>
          <div class="action-row"><button id="reset-selected-device" type="button" class="secondary">清除裝置授權</button></div>
        </section>

        <section id="users-admin" class="dashboard-canvas-panel dashboard-canvas-panel-wide" data-dashboard-panel="users-admin" data-dashboard-title="使用者清單" hidden>
          <h2>Users</h2>
          <div class="table-wrap">
            <table class="admin-table">
              <thead><tr><th>Username</th><th>Role</th><th>Status</th><th>Classes</th><th>身分同步</th><th>密碼 / 同步</th><th>操作</th></tr></thead>
              <tbody>${users.map(renderUserRow).join('')}</tbody>
            </table>
          </div>
        </section>

        <section id="weeks-admin" class="dashboard-canvas-panel" data-dashboard-panel="weeks-admin" data-dashboard-title="班級週次" hidden>
          <h2>班級 Week 開關</h2>
          ${CLASSES.map(({ id, label }) => renderClassAccessEditor(id, label, weeks, classAccess[id] ?? [])).join('')}
        </section>
      </div>
    </section>
  `);

  initDashboardTabs();
  document.querySelector('#logout')!.addEventListener('click', () => { logout(); renderLogin(); });
  document.querySelector('#save-user')!.addEventListener('click', saveUser);
  document.querySelector('#clear-user-form')!.addEventListener('click', clearUserForm);
  document.querySelector('#reset-selected-device')!.addEventListener('click', resetSelectedStudentDevice);
  document.querySelector('#generate-temporary-password')!.addEventListener('click', () => {
    setValue('#temporary-password', generateTemporaryPassword());
  });
  setValue('#temporary-password', generateTemporaryPassword());
  document.querySelectorAll<HTMLElement>('[data-edit-user]').forEach((button) => button.addEventListener('click', () => {
    const username = button.dataset.editUser!;
    const user = users.find((candidate) => candidate.username === username);
    if (user) populateUserForm(user);
  }));
  document.querySelectorAll<HTMLElement>('[data-reset-sync-user]').forEach((button) => button.addEventListener('click', async () => {
    await resetAndSyncUser(button.dataset.resetSyncUser!);
  }));
  document.querySelectorAll<HTMLElement>('[data-generate-password-for]').forEach((button) => button.addEventListener('click', () => {
    const username = button.dataset.generatePasswordFor!;
    const passwordInput = document.querySelector<HTMLInputElement>(`input[data-reset-password-for="${cssEscape(username)}"]`);
    if (passwordInput) passwordInput.value = generateTemporaryPassword();
  }));
  document.querySelectorAll<HTMLElement>('[data-save-class]').forEach((button) => button.addEventListener('click', async () => {
    await saveClassAccess(button.dataset.saveClass as ClassId);
  }));
  document.querySelectorAll<HTMLElement>('[data-delete-user]').forEach((button) => button.addEventListener('click', async () => {
    await deleteUser(button.dataset.deleteUser!);
  }));
}

function renderUserRow(user: UserProfile): string {
  const statusClass = user.identity_sync_status === 'failed' ? 'status-bad' : 'status-ok';
  return `
    <tr>
      <td><strong>${escapeHtml(user.username)}</strong></td>
      <td>${escapeHtml(user.role)}</td>
      <td>${escapeHtml(user.status)}</td>
      <td>${user.classes.length ? user.classes.map(classBadge).join(' ') : '<span class="muted">—</span>'}</td>
      <td><span class="${statusClass}">${escapeHtml(user.identity_sync_status ?? 'unknown')}</span>${user.identity_sync_error ? `<div class="hint">${escapeHtml(user.identity_sync_error)}</div>` : ''}</td>
      <td><div class="cell-actions"><input class="inline-input" data-reset-password-for="${escapeHtml(user.username)}" type="text" placeholder="新臨時密碼"><button class="secondary" data-generate-password-for="${escapeHtml(user.username)}">產生</button><button data-reset-sync-user="${escapeHtml(user.username)}">重設密碼並同步</button></div></td>
      <td><div class="cell-actions"><button class="secondary" data-edit-user="${escapeHtml(user.username)}">帶入編輯</button><button class="danger" data-delete-user="${escapeHtml(user.username)}">刪除帳號</button></div></td>
    </tr>
  `;
}

function renderClassAccessEditor(classId: ClassId, label: string, weeks: WeekSummary[], selectedWeekIds: string[]): string {
  return `
    <div class="class-access-panel">
      <h3>${escapeHtml(label)}</h3>
      <fieldset class="choice-list week-choice-list">
        <legend>開放 Weeks</legend>
        ${weeks.length ? weeks.map((week) => `
          <label class="choice"><input type="checkbox" name="open-week-${classId}" value="${escapeHtml(week.week_id)}" ${selectedWeekIds.includes(week.week_id) ? 'checked' : ''}> Week ${escapeHtml(week.week_number)} — ${escapeHtml(formatDisplayName(week.title))}</label>
        `).join('') : '<p class="muted">尚未建立 Week。請先用 teacher 建立教材。</p>'}
      </fieldset>
      <button data-save-class="${classId}">儲存 ${escapeHtml(label)} 開放 Week</button>
    </div>
  `;
}

function studentOptions(users: UserProfile[]): string {
  const students = users.filter((user) => user.role === 'student');
  const options = students.map((student) => {
    const boundLabel = student.device_id ? '已授權裝置' : '尚未授權裝置';
    return `<option value="${escapeHtml(student.username)}">${escapeHtml(student.username)} — ${boundLabel}</option>`;
  }).join('');
  return `<option value="">請選擇學生</option>${options}`;
}

function classCheckboxes(name: string, selectedClasses: ClassId[]): string {
  return CLASSES.map(({ id, label }) => `<label class="choice"><input type="checkbox" name="${name}" value="${id}" ${selectedClasses.includes(id) ? 'checked' : ''}> ${label}</label>`).join('');
}

function classBadge(classId: ClassId): string {
  const label = CLASSES.find((entry) => entry.id === classId)?.label ?? classId;
  return `<span class="badge">${escapeHtml(label)}</span>`;
}

async function saveUser(): Promise<void> {
  if (!token) return renderLogin();
  try {
    const temporaryPassword = value('#temporary-password');
    await apiFetchWithSession('/admin/users', {
      method: 'POST',
      body: JSON.stringify({
        username: value('#user-username'),
        role: value('#role'),
        status: value('#status'),
        classes: checkboxValues<ClassId>('user-class'),
        temporary_password: temporaryPassword || undefined
      })
    });
    await renderAdmin();
    if (temporaryPassword) showMessage(`帳號已儲存。臨時密碼：${temporaryPassword}`);
  } catch (error) { showError(error); }
}

async function resetAndSyncUser(username: string): Promise<void> {
  if (!token) return renderLogin();
  const passwordInput = document.querySelector<HTMLInputElement>(`input[data-reset-password-for="${cssEscape(username)}"]`);
  const temporaryPassword = passwordInput?.value.trim() ?? '';
  if (!temporaryPassword) {
    showError(new Error('請輸入新臨時密碼後再重設並同步。密碼至少10碼，需含大小寫與數字。'));
    return;
  }
  try {
    await apiFetchWithSession(`/admin/users/${encodeURIComponent(username)}/sync-identity`, {
      method: 'POST',
      body: JSON.stringify({ temporary_password: temporaryPassword })
    });
    await apiFetchWithSession('/admin/users/password-reset', {
      method: 'POST',
      body: JSON.stringify({ username, temporary_password: temporaryPassword })
    });
    await renderAdmin();
    showMessage(`${username} 已重設密碼並同步。臨時密碼：${temporaryPassword}`);
  } catch (error) { showError(error); }
}

async function resetSelectedStudentDevice(): Promise<void> {
  if (!token) return renderLogin();
  const username = value('#reset-device-student');
  if (!username) return showError(new Error('請先選擇要清除裝置授權的學生。'));
  if (!(await showConfirmModal(`確認清除 ${username} 的裝置授權？`, { confirmLabel: '確認清除' }))) return;
  try {
    await apiFetchWithSession('/device/reset', {
      method: 'POST',
      body: JSON.stringify({ username })
    });
    await renderAdmin();
    showMessage(`${username} 的裝置授權已清除。`);
  } catch (error) { showError(error); }
}

async function deleteUser(username: string): Promise<void> {
  if (!token) return renderLogin();
  if (!(await showConfirmModal(`確認刪除帳號 ${username}？此操作無法復原。`, { confirmLabel: '刪除帳號', danger: true }))) return;
  try {
    await apiFetchWithSession(`/admin/users/${encodeURIComponent(username)}`, { method: 'DELETE' });
    await renderAdmin();
    showMessage(`${username} 已刪除。`);
  } catch (error) { showError(error); }
}

async function saveClassAccess(classId: ClassId): Promise<void> {
  if (!token) return renderLogin();
  try {
    await apiFetchWithSession(`/admin/classes/${classId}/open-weeks`, {
      method: 'PUT',
      body: JSON.stringify({ open_week_ids: checkboxValues(`open-week-${classId}`) })
    });
    showMessage('班級 Week 開關已儲存。');
    await renderAdmin();
  } catch (error) { showError(error); }
}

function populateUserForm(user: UserProfile): void {
  setValue('#user-username', user.username);
  setValue('#role', user.role);
  setValue('#status', user.status);
  setValue('#temporary-password', '');
  document.querySelectorAll<HTMLInputElement>('input[name="user-class"]').forEach((input) => {
    input.checked = user.classes.includes(input.value as ClassId);
  });
  activateDashboardPanel('account-admin');
  document.querySelector('#user-username')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function clearUserForm(): void {
  setValue('#user-username', '');
  setValue('#role', 'student');
  setValue('#status', 'active');
  setValue('#temporary-password', generateTemporaryPassword());
  document.querySelectorAll<HTMLInputElement>('input[name="user-class"]').forEach((input) => { input.checked = false; });
}

function initDashboardTabs(): void {
  document.querySelectorAll<HTMLButtonElement>('[data-dashboard-target]').forEach((button) => {
    button.addEventListener('click', () => activateDashboardPanel(button.dataset.dashboardTarget ?? ''));
  });
}

function activateDashboardPanel(panelId: string): void {
  const targetPanel = document.querySelector<HTMLElement>(`[data-dashboard-panel="${cssEscape(panelId)}"]`);
  if (!targetPanel) return;
  document.querySelectorAll<HTMLElement>('[data-dashboard-panel]').forEach((panel) => {
    panel.hidden = panel !== targetPanel;
  });
  document.querySelectorAll<HTMLButtonElement>('[data-dashboard-target]').forEach((button) => {
    const isActive = button.dataset.dashboardTarget === panelId;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-selected', String(isActive));
  });
  const title = document.querySelector<HTMLElement>('#dashboard-title');
  if (title) title.textContent = targetPanel.dataset.dashboardTitle ?? '';
}

function value(selector: string): string { return document.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!.value.trim(); }
function setValue(selector: string, nextValue: string): void { document.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!.value = nextValue; }
function checkboxValues<T extends string = string>(name: string): T[] {
  return Array.from(document.querySelectorAll<HTMLInputElement>(`input[name="${name}"]:checked`)).map((input) => input.value as T);
}
function cssEscape(valueToEscape: string): string {
  return globalThis.CSS?.escape ? globalThis.CSS.escape(valueToEscape) : valueToEscape.replace(/"/g, '\\"');
}

getCurrentToken()
  .then((existing) => { token = existing; return token ? renderAdmin() : renderLogin(); })
  .catch(showError);
registerAppServiceWorker();
