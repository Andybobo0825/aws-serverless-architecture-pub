import './styles.css';
import type { Me, WeekSummary } from './types';
import { ApiFetchError, apiFetch } from './api';
import { completeNewPassword, getCurrentToken, login, logout } from './auth';
import { getOrCreateDeviceId } from './device';
import { showConfirmModal, showResponseModal } from './modal';
import { registerAppServiceWorker } from './pwa';
import { renderLoading } from './loading';

interface MagicPageUrl {
  name: string;
  url: string;
}

interface UrlCard {
  name: string;
  url: string;
}

interface ImageCard {
  name: string;
  image_key: string;
  content_type: string;
  url?: string;
}

interface ImageUploadResponse {
  image_key: string;
  content_type: string;
  upload_url: string;
}

interface WeekDetail {
  week_id: string;
  week_number: number;
  title: string;
  class_id?: ClassId | null;
  magic_pages: string[];
  magic_page_urls: MagicPageUrl[];
  url_cards: UrlCard[];
  image_cards: ImageCard[];
}

interface ContentMagicPage {
  key: string;
  name: string;
  url?: string | null;
}

interface ContentAssets {
  magic_pages: ContentMagicPage[];
}

type ClassId = 'jul' | 'aug';

interface ClassAccess {
  class_id: ClassId;
  open_week_ids: string[];
}

interface TeacherDashboard {
  class_access: ClassAccess[];
  class_weeks: Record<ClassId, WeekSummary[]>;
  assets: ContentAssets;
}

const CLASSES: Array<{ id: ClassId; label: string }> = [
  { id: 'jul', label: '7月班' },
  { id: 'aug', label: '8月班' }
];

const app = document.querySelector<HTMLDivElement>('#app');
if (!app) throw new Error('missing #app');
let token: string | null = null;
let currentRole: Me['role'] | null = null;
let teacherWeeks: WeekSummary[] = [];
let teacherWeeksByClass: Record<ClassId, WeekSummary[]> = { jul: [], aug: [] };
let teacherAssets: ContentAssets = { magic_pages: [] };
let teacherClassAccess: Record<ClassId, string[]> = { jul: [], aug: [] };
let selectedTeacherClass: ClassId = 'jul';
let selectedStudentClass: ClassId | null = null;
let editingUrlCards: UrlCard[] = [];
let editingUrlCardIndex: number | null = null;
let editingImageCards: ImageCard[] = [];

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

function setHtml(html: string): void { app!.innerHTML = html; }
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
function showMessage(message: string): void { void showResponseModal(message, { title: '提示' }); }
function value(selector: string): string { return document.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!.value.trim(); }
function setValue(selector: string, nextValue: string): void { document.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!.value = nextValue; }

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
function checkboxValues(name: string): string[] {
  return Array.from(document.querySelectorAll<HTMLInputElement>(`input[name="${name}"]:checked`)).map((input) => input.value);
}
function cssEscape(valueToEscape: string): string {
  return globalThis.CSS?.escape ? globalThis.CSS.escape(valueToEscape) : valueToEscape.replace(/"/g, '\\"');
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

function renderLogin(): void {
  setHtml(`
    <form id="login-form" class="card">
      <h1>Magic Login</h1>

      <label>Username <input id="username" autocomplete="username"></label>
      <label>Password <span class="password-field"><input id="password" type="password" autocomplete="current-password"><button type="button" class="secondary" data-password-toggle="password">顯示密碼</button></span></label>
      <button id="login" type="submit">登入</button>
    </form>
  `);
  bindPasswordToggles();
  document.querySelector('#login-form')!.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const username = value('#username');
      const password = value('#password');
      renderLoading(app!, '登入中');
      const result = await login(username, password);
      if (result.requiredNewPassword && result.challengeUser) {
        renderChangePassword(result.challengeUser);
        return;
      }
      token = result.token ?? null;
      await renderHome();
    } catch (error) { renderLogin(); showError(error); }
  });
}

function renderChangePassword(challengeUser: Parameters<typeof completeNewPassword>[0]): void {
  setHtml(`
    <form id="change-password-form" class="card">
      <h1>首次登入改密碼</h1>

      <label>New password <span class="password-field"><input id="new-password" type="password"><button type="button" class="secondary" data-password-toggle="new-password">顯示密碼</button></span></label>
      <button id="change" type="submit">更新密碼</button>
    </form>
  `);
  bindPasswordToggles();
  document.querySelector('#change-password-form')!.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const newPassword = value('#new-password');
      renderLoading(app!, '登入中');
      token = await completeNewPassword(challengeUser, newPassword);
      await renderHome();
    } catch (error) { renderChangePassword(challengeUser); showError(error); }
  });
}

async function renderHome(): Promise<void> {
  if (!token) return renderLogin();
  const me = await apiFetchWithSession<Me>('/me');
  currentRole = me.role;
  if (me.role === 'student' && !me.device_bound) {
    await apiFetchWithSession('/device/register', { method: 'POST', body: JSON.stringify({ device_id: getOrCreateDeviceId() }) });
  }
  const studentClasses = me.role === 'student' ? studentClassIds(me) : [];
  if (me.role === 'student' && studentClasses.length && !studentClasses.includes(selectedStudentClass as ClassId)) {
    selectedStudentClass = studentClasses[0];
  }
  const weeks = me.role === 'teacher'
    ? await apiFetchWithSession<WeekSummary[]>(`/teacher/classes/${selectedTeacherClass}/weeks`)
    : selectedStudentClass
      ? await apiFetchWithSession<WeekSummary[]>(`/student/classes/${selectedStudentClass}/weeks`)
      : await apiFetchWithSession<WeekSummary[]>('/student/weeks');
  setHtml(`
    <div class="toolbar"><h1>Magic Weeks</h1><span>${escapeHtml(me.username)} (${escapeHtml(me.role)})</span><button id="logout" class="secondary">登出</button></div>
    ${me.role === 'teacher' ? `
      <div class="action-row">
        <label>主畫面班別 ${teacherHomeClassSelect()}</label>
        <button id="teacher-panel">教材與週次管理</button>
      </div>
    ` : ''}
    ${me.role === 'student' && studentClasses.length > 1 ? `
      <div class="action-row">
        <label>我的班級 ${studentHomeClassSelect(studentClasses)}</label>
      </div>
    ` : ''}
    <section class="grid">${weeks.map((week) => {
    const isOpen = week.is_open || me.role === 'teacher';
    return `<article class="week ${isOpen ? '' : 'locked'}" data-week="${escapeHtml(week.week_id)}" data-open="${isOpen}"><h2>Week ${escapeHtml(week.week_number)}</h2><p>${escapeHtml(formatDisplayName(week.title))}</p></article>`;
  }).join('')}</section>
  `);
  document.querySelector('#logout')!.addEventListener('click', () => { logout(); renderLogin(); });
  document.querySelector('#teacher-home-class-selector')?.addEventListener('change', () => {
    selectedTeacherClass = value('#teacher-home-class-selector') as ClassId;
    void renderHome().catch(showError);
  });
  document.querySelector('#student-home-class-selector')?.addEventListener('change', () => {
    selectedStudentClass = value('#student-home-class-selector') as ClassId;
    void renderHome().catch(showError);
  });
  document.querySelectorAll<HTMLElement>('.week').forEach((el) => el.addEventListener('click', () => {
    if (el.dataset.open === 'true' && el.dataset.week) void renderWeek(el.dataset.week).catch(showError);
  }));
  document.querySelector('#teacher-panel')?.addEventListener('click', () => { void renderTeacherPanel().catch(showError); });
}

function teacherHomeClassSelect(): string {
  const options = CLASSES.map(({ id, label }) => `<option value="${id}" ${id === selectedTeacherClass ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('');
  return `<select id="teacher-home-class-selector">${options}</select>`;
}

function studentClassIds(me: Me): ClassId[] {
  return me.classes.filter((classId): classId is ClassId => classId === 'jul' || classId === 'aug');
}

function studentHomeClassSelect(classIds: ClassId[]): string {
  const options = CLASSES
    .filter(({ id }) => classIds.includes(id))
    .map(({ id, label }) => `<option value="${id}" ${id === selectedStudentClass ? 'selected' : ''}>${escapeHtml(label)}</option>`)
    .join('');
  return `<select id="student-home-class-selector">${options}</select>`;
}

async function renderWeek(weekId: string): Promise<void> {
  if (!token) return renderLogin();
  const path = currentRole === 'teacher' ? `/teacher/weeks/${weekId}` : `/student/weeks/${weekId}`;
  const detail = await apiFetchWithSession<WeekDetail>(path);
  const s3Cards = detail.magic_page_urls.map((page) => ({
    name: formatDisplayName(page.name),
    url: page.url
  }));
  const urlCards = (detail.url_cards ?? []).map((card) => ({
    name: card.name,
    url: card.url
  }));
  const imageCards = (detail.image_cards ?? []).filter((card) => card.url);
  const materialCards = [...s3Cards, ...urlCards];
  const contentCards = materialCards.map((card) => `
    <a class="content-card" href="${escapeHtml(card.url)}" target="_blank" rel="noopener noreferrer" data-url="${escapeHtml(card.url)}" data-name="${escapeHtml(card.name)}">
      <span>${escapeHtml(card.name)}</span>
    </a>
  `).join('');
  const imageContentCards = imageCards.map((card) => `
    <a class="content-card image-material-card" href="${escapeHtml(card.url)}" target="_blank" rel="noopener noreferrer" data-url="${escapeHtml(card.url)}" data-name="${escapeHtml(card.name)}">
      <img src="${escapeHtml(card.url)}" alt="${escapeHtml(card.name)}" loading="lazy">
      <span>${escapeHtml(card.name)}</span>
    </a>
  `).join('');
  setHtml(`
    <button id="back" class="secondary">← Back</button>
    <section class="content-shell">
      <header class="content-header"><h1>${escapeHtml(detail.title)}</h1></header>
      <section class="external-content-panel" aria-live="polite">
        <h2>教材連結</h2>
        <div class="content-list material-card-grid compact-material-grid" aria-label="Week 教材連結">
          ${contentCards || '<p class="card muted">尚未設定課程教材。</p>'}
        </div>
        <h2>圖片教材</h2>
        <div class="content-list material-card-grid image-card-grid" aria-label="Week 圖片教材">
          ${imageContentCards || '<p class="card muted">尚未設定圖片教材。</p>'}
        </div>
      </section>
    </section>
  `);
  initDashboardTabs();
  document.querySelector('#back')!.addEventListener('click', () => { void renderHome().catch(showError); });
  document.querySelectorAll<HTMLAnchorElement>('.content-card').forEach((card) => {
    card.addEventListener('click', (event) => openMaterialCard(event, card));
  });
}

function openMaterialCard(event: MouseEvent, card: HTMLAnchorElement): void {
  const url = card.dataset.url;
  if (!url) return;
  event.preventDefault();
  window.open(url, '_blank', 'noopener');
}

async function renderTeacherPanel(): Promise<void> {
  if (!token) return renderLogin();
  const dashboard = await apiFetchWithSession<TeacherDashboard>('/teacher/dashboard');
  teacherAssets = dashboard.assets;
  teacherClassAccess = Object.fromEntries(dashboard.class_access.map((access) => [access.class_id, access.open_week_ids])) as Record<ClassId, string[]>;
  teacherWeeksByClass = {
    jul: dashboard.class_weeks.jul ?? [],
    aug: dashboard.class_weeks.aug ?? []
  };
  teacherWeeks = teacherWeeksByClass[selectedTeacherClass] ?? [];
  editingUrlCards = [];
  editingUrlCardIndex = null;
  editingImageCards = [];
  setHtml(`
    <div class="toolbar"><h1>教材與週次管理</h1><button id="back" class="secondary">回 Week</button></div>

    <section class="dashboard-shell management-dashboard" aria-label="Teacher management dashboard">
      <aside class="dashboard-rail" aria-label="Teacher function buttons">
        <button type="button" class="dashboard-rail-button active" data-dashboard-target="week-editor" aria-selected="true">週內容</button>
        <button type="button" class="dashboard-rail-button" data-dashboard-target="class-visibility" aria-selected="false">班級可見週次</button>
        <button type="button" class="dashboard-rail-button" data-dashboard-target="week-overview" aria-selected="false">目前 Weeks</button>
      </aside>
      <div class="dashboard-canvas">
        <header class="dashboard-canvas-header">
          <div><p class="eyebrow">Teacher Dashboard</p><h2 id="dashboard-title">週內容</h2></div>
        </header>
        <section id="week-editor" class="dashboard-canvas-panel" data-dashboard-panel="week-editor" data-dashboard-title="週內容">
          <h2>週主題與教材</h2>
          <p class="muted">設定週主題、綁定教材連結，並儲存給學生端顯示。7月與8月會分開管理，不會互相同步覆蓋。</p>
          <div class="form-grid">
            <label>管理班別 ${teacherClassSelect()}</label>
            <label>Week number ${weekNumberSelect()}</label>
            <label>週主題名稱 <input id="week-title" placeholder="例如：讀心術入門"></label>
          </div>
          <fieldset class="choice-list week-choice-list">
            <legend>課程教材</legend>
            ${magicPageChoices()}
          </fieldset>
          <section class="url-card-editor sub-panel">
            <h2>新增連結教材</h2>
            <p class="muted">老師貼上連結後，必須輸入 Card 名稱。</p>
            <div class="form-grid">
              <label>Card 名稱 <input id="url-card-name" placeholder="例如：課前講義"></label>
              <label>連結 <input id="url-card-url" type="url" placeholder="https://example.com/lesson"></label>
            </div>
            <div class="action-row"><button id="add-url-card" type="button" class="secondary">新增連結 Card</button><button id="cancel-url-card-edit" type="button" class="secondary" hidden>取消編輯</button></div>
            <div id="url-card-list" class="url-card-list"></div>
          </section>
          <section class="image-card-editor sub-panel">
            <h2>新增圖片教材</h2>
            <p class="muted">支援 JPG、PNG、WebP，單張最多 5MB。不同圖片比例會完整顯示，不強制裁切。</p>
            <div class="form-grid">
              <label>圖片名稱 <input id="image-card-name" placeholder="例如：課堂白板"></label>
              <label>圖片檔案 <input id="image-card-file" type="file" accept="image/jpeg,image/png,image/webp"></label>
            </div>
            <div class="action-row"><button id="add-image-card" type="button" class="secondary">新增圖片 Card</button></div>
            <div id="image-card-list" class="url-card-list"></div>
          </section>
          <div class="action-row"><button id="save-week-material">儲存週主題與教材</button><button id="delete-week-material" type="button" class="danger" data-delete-week>硬刪除此 Week</button></div>
        </section>
        <section id="class-visibility" class="dashboard-canvas-panel" data-dashboard-panel="class-visibility" data-dashboard-title="班級可見週次" hidden>
          <h2>教師決定各班可見週次</h2>
          ${CLASSES.map(({ id, label }) => renderTeacherClassAccessEditor(id, label)).join('')}
        </section>
        <section id="week-overview" class="dashboard-canvas-panel" data-dashboard-panel="week-overview" data-dashboard-title="目前 Weeks" hidden>
          <h2>目前 Weeks</h2>
          <p class="muted">目前顯示 ${escapeHtml(classLabel(selectedTeacherClass))} 的 Week。</p>
          ${teacherWeeks.length ? `<div class="week-overview-grid">${teacherWeeks.map((week) => `<article class="week mini-week"><h3>Week ${escapeHtml(week.week_number)}</h3><p>${escapeHtml(week.title)}</p></article>`).join('')}</div>` : '<p class="muted">尚未建立 Week。</p>'}
        </section>
      </div>
    </section>
  `);
  initDashboardTabs();
  document.querySelector('#back')!.addEventListener('click', () => { void renderHome().catch(showError); });
  document.querySelector('#teacher-class-selector')!.addEventListener('change', () => {
    selectedTeacherClass = value('#teacher-class-selector') as ClassId;
    void renderTeacherPanel().catch(showError);
  });
  document.querySelector('#week-number')!.addEventListener('change', () => loadSelectedWeekIntoForm());
  document.querySelector('#add-url-card')!.addEventListener('click', addUrlCardFromForm);
  document.querySelector('#cancel-url-card-edit')!.addEventListener('click', cancelUrlCardEdit);
  document.querySelector('#add-image-card')!.addEventListener('click', () => { void addImageCardFromForm(); });
  document.querySelector('#save-week-material')!.addEventListener('click', saveWeekMaterial);
  document.querySelector('#delete-week-material')!.addEventListener('click', deleteSelectedWeek);
  document.querySelectorAll<HTMLElement>('[data-save-teacher-class]').forEach((button) => button.addEventListener('click', async () => {
    await saveTeacherClassAccess(button.dataset.saveTeacherClass as ClassId);
  }));
  await loadSelectedWeekIntoForm();
}

function classLabel(classId: ClassId): string {
  return CLASSES.find(({ id }) => id === classId)?.label ?? classId;
}

function teacherClassSelect(): string {
  const options = CLASSES.map(({ id, label }) => `<option value="${id}" ${id === selectedTeacherClass ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('');
  return `<select id="teacher-class-selector">${options}</select>`;
}

function weekNumberSelect(): string {
  const existingNumbers = new Set(teacherWeeks.map((week) => week.week_number));
  const maxWeek = Math.max(12, ...Array.from(existingNumbers), 1);
  const options = Array.from({ length: maxWeek }, (_, index) => index + 1).map((weekNumber) => {
    const existing = teacherWeeks.find((week) => week.week_number === weekNumber);
    const label = existing ? `Week ${weekNumber} — ${existing.title}` : `Week ${weekNumber}`;
    const optionValue = existing?.week_id ?? `new:${weekNumber}`;
    return `<option value="${escapeHtml(optionValue)}">${escapeHtml(label)}</option>`;
  }).join('');
  return `<select id="week-number">${options}</select>`;
}

function magicPageChoices(): string {
  if (!teacherAssets.magic_pages.length) return '<p class="muted">目前沒有可選教材。</p>';
  return teacherAssets.magic_pages.map((page) => `<label class="choice"><input class="magic-page-choice" type="checkbox" name="magic-page-choice" value="${escapeHtml(page.name)}"> ${escapeHtml(formatDisplayName(page.name))}</label>`).join('');
}

function renderTeacherClassAccessEditor(classId: ClassId, label: string): string {
  const selectedWeekIds = teacherClassAccess[classId] ?? [];
  const classWeeks = teacherWeeksByClass[classId] ?? [];
  return `
    <div class="class-access-panel">
      <h3>${escapeHtml(label)}</h3>
      <fieldset class="choice-list week-choice-list">
        <legend>開放 Weeks</legend>
        ${classWeeks.length ? classWeeks.map((week) => `
          <label class="choice"><input type="checkbox" name="teacher-open-week-${classId}" value="${escapeHtml(week.week_id)}" ${selectedWeekIds.includes(week.week_id) ? 'checked' : ''}> Week ${escapeHtml(week.week_number)} — ${escapeHtml(formatDisplayName(week.title))}</label>
        `).join('') : '<p class="muted">尚未建立 Week。請先建立教材週次。</p>'}
      </fieldset>
      <button data-save-teacher-class="${classId}">儲存 ${escapeHtml(label)} 可見 Week</button>
    </div>
  `;
}

async function loadSelectedWeekIntoForm(): Promise<void> {
  if (!token) return renderLogin();
  const selectedWeek = selectedTeacherWeek();
  clearMagicPageChoices();
  editingUrlCards = [];
  editingUrlCardIndex = null;
  editingImageCards = [];
  resetUrlCardForm();
  resetImageCardForm();
  if (!selectedWeek) {
    setValue('#week-title', '');
    renderUrlCardList();
    renderImageCardList();
    return;
  }
  const detail = await apiFetchWithSession<WeekDetail>(`/teacher/weeks/${selectedWeek.week_id}`);
  setValue('#week-title', detail.title);
  editingUrlCards = [...(detail.url_cards ?? [])];
  editingImageCards = [...(detail.image_cards ?? [])];
  document.querySelectorAll<HTMLInputElement>('input[name="magic-page-choice"]').forEach((input) => {
    input.checked = detail.magic_pages.includes(input.value);
  });
  renderUrlCardList();
  renderImageCardList();
}

function selectedTeacherWeek(): WeekSummary | null {
  return teacherWeeks.find((week) => week.week_id === value('#week-number')) ?? null;
}

function selectedTeacherWeekNumber(): number {
  const selectedWeek = selectedTeacherWeek();
  if (selectedWeek) return selectedWeek.week_number;
  const selectedValue = value('#week-number');
  if (selectedValue.startsWith('new:')) return Number(selectedValue.replace('new:', ''));
  return Number(selectedValue);
}

function addUrlCardFromForm(): void {
  const name = value('#url-card-name');
  const url = value('#url-card-url');
  if (!name || !url) return showError(new Error('請輸入 Card 名稱與連結。'));
  try {
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('invalid protocol');
  } catch {
    showError(new Error('連結必須是有效的 http 或 https。'));
    return;
  }
  if (editingUrlCardIndex === null) {
    editingUrlCards.push({ name, url });
  } else {
    editingUrlCards[editingUrlCardIndex] = { name, url };
  }
  resetUrlCardForm();
  renderUrlCardList();
}

function cancelUrlCardEdit(): void {
  resetUrlCardForm();
  renderUrlCardList();
}

function resetUrlCardForm(): void {
  editingUrlCardIndex = null;
  setValue('#url-card-name', '');
  setValue('#url-card-url', '');
  const addButton = document.querySelector<HTMLButtonElement>('#add-url-card');
  const cancelButton = document.querySelector<HTMLButtonElement>('#cancel-url-card-edit');
  if (addButton) addButton.textContent = '新增連結 Card';
  if (cancelButton) cancelButton.hidden = true;
}

function startEditingUrlCard(index: number): void {
  const card = editingUrlCards[index];
  if (!card) return;
  editingUrlCardIndex = index;
  setValue('#url-card-name', card.name);
  setValue('#url-card-url', card.url);
  const addButton = document.querySelector<HTMLButtonElement>('#add-url-card');
  const cancelButton = document.querySelector<HTMLButtonElement>('#cancel-url-card-edit');
  if (addButton) addButton.textContent = '更新連結 Card';
  if (cancelButton) cancelButton.hidden = false;
}

function renderUrlCardList(): void {
  const target = document.querySelector<HTMLElement>('#url-card-list');
  if (!target) return;
  target.innerHTML = editingUrlCards.length ? editingUrlCards.map((card, index) => `
    <article class="content-card url-card-preview">
      <span>${escapeHtml(card.name)}</span>
      <div class="url-card-actions"><button type="button" class="secondary" data-edit-url-card="${index}">編輯</button><button type="button" class="secondary" data-remove-url-card="${index}">移除</button></div>
    </article>
  `).join('') : '<p class="muted">尚未新增連結 Card。</p>';
  target.querySelectorAll<HTMLButtonElement>('[data-edit-url-card]').forEach((button) => {
    button.addEventListener('click', () => startEditingUrlCard(Number(button.dataset.editUrlCard)));
  });
  target.querySelectorAll<HTMLButtonElement>('[data-remove-url-card]').forEach((button) => {
    button.addEventListener('click', () => {
      const removedIndex = Number(button.dataset.removeUrlCard);
      editingUrlCards.splice(removedIndex, 1);
      if (editingUrlCardIndex === removedIndex) resetUrlCardForm();
      if (editingUrlCardIndex !== null && removedIndex < editingUrlCardIndex) editingUrlCardIndex -= 1;
      renderUrlCardList();
    });
  });
}

function resetImageCardForm(): void {
  setValue('#image-card-name', '');
  const input = document.querySelector<HTMLInputElement>('#image-card-file');
  if (input) input.value = '';
}

function selectedImageFile(): File | null {
  return document.querySelector<HTMLInputElement>('#image-card-file')?.files?.[0] ?? null;
}

function validateImageFile(file: File): void {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    throw new Error('圖片只支援 JPG、PNG、WebP。');
  }
  if (file.size > 5 * 1024 * 1024) {
    throw new Error('圖片單張最多 5MB。');
  }
}

async function ensureWeekForImageUpload(): Promise<string> {
  if (!token) throw new Error('尚未登入。');
  const weekNumber = selectedTeacherWeekNumber();
  const title = value('#week-title') || `Week ${weekNumber}`;
  const existing = selectedTeacherWeek();
  if (existing && existing.class_id !== null && existing.class_id !== undefined) return existing.week_id;
  const created = await apiFetchWithSession<WeekSummary>(`/teacher/classes/${selectedTeacherClass}/weeks`, {
    method: 'POST',
    body: JSON.stringify({ week_number: weekNumber, title, class_id: selectedTeacherClass })
  });
  teacherWeeks.push(created);
  teacherWeeksByClass[selectedTeacherClass] = [...(teacherWeeksByClass[selectedTeacherClass] ?? []), created];
  const select = document.querySelector<HTMLSelectElement>('#week-number');
  const selectedOption = select?.selectedOptions[0];
  if (selectedOption) {
    selectedOption.value = created.week_id;
    selectedOption.textContent = `Week ${created.week_number} — ${created.title}`;
  }
  return created.week_id;
}

async function addImageCardFromForm(): Promise<void> {
  if (!token) return renderLogin();
  const name = value('#image-card-name');
  const file = selectedImageFile();
  if (!name || !file) return showError(new Error('請輸入圖片名稱並選擇圖片檔案。'));
  try {
    validateImageFile(file);
    const targetWeekId = await ensureWeekForImageUpload();
    const upload = await apiFetchWithSession<ImageUploadResponse>(`/teacher/weeks/${targetWeekId}/image-upload`, {
      method: 'POST',
      body: JSON.stringify({ filename: file.name, content_type: file.type })
    });
    const uploadResponse = await fetch(upload.upload_url, {
      method: 'PUT',
      headers: { 'content-type': upload.content_type },
      body: file
    });
    if (!uploadResponse.ok) throw new Error(`圖片上傳失敗：${uploadResponse.status}`);
    editingImageCards.push({
      name,
      image_key: upload.image_key,
      content_type: upload.content_type,
      url: URL.createObjectURL(file)
    });
    resetImageCardForm();
    renderImageCardList();
  } catch (error) { showError(error); }
}

function renderImageCardList(): void {
  const target = document.querySelector<HTMLElement>('#image-card-list');
  if (!target) return;
  target.innerHTML = editingImageCards.length ? editingImageCards.map((card, index) => `
    <article class="content-card url-card-preview image-card-preview">
      ${card.url ? `<img src="${escapeHtml(card.url)}" alt="${escapeHtml(card.name)}">` : ''}
      <span>${escapeHtml(card.name)}</span>
      <small>${escapeHtml(card.content_type)}</small>
      <div class="url-card-actions"><button type="button" class="secondary" data-remove-image-card="${index}">移除</button></div>
    </article>
  `).join('') : '<p class="muted">尚未新增圖片 Card。</p>';
  target.querySelectorAll<HTMLButtonElement>('[data-remove-image-card]').forEach((button) => {
    button.addEventListener('click', () => {
      editingImageCards.splice(Number(button.dataset.removeImageCard), 1);
      renderImageCardList();
    });
  });
}

function clearMagicPageChoices(): void {
  document.querySelectorAll<HTMLInputElement>('input[name="magic-page-choice"]').forEach((input) => { input.checked = false; });
}

async function saveWeekMaterial(): Promise<void> {
  if (!token) return renderLogin();
  const weekNumber = selectedTeacherWeekNumber();
  const selectedMagicPages = checkboxValues('magic-page-choice');
  if (!selectedMagicPages.length && !editingUrlCards.length && !editingImageCards.length) return showError(new Error('請至少選擇一個教材或新增一張連結/圖片 Card。'));
  const title = value('#week-title') || `Week ${weekNumber}`;
  try {
    const existing = selectedTeacherWeek();
    let targetWeekId = existing?.week_id;
    if (!targetWeekId || existing?.class_id === null || existing?.class_id === undefined) {
      const created = await apiFetchWithSession<WeekSummary>(`/teacher/classes/${selectedTeacherClass}/weeks`, {
        method: 'POST',
        body: JSON.stringify({ week_number: weekNumber, title, class_id: selectedTeacherClass })
      });
      targetWeekId = created.week_id;
    }
    await apiFetchWithSession(`/teacher/weeks/${targetWeekId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        title,
        magic_pages: selectedMagicPages,
        url_cards: editingUrlCards,
        image_cards: editingImageCards.map((card) => ({
          name: card.name,
          image_key: card.image_key,
          content_type: card.content_type
        }))
      })
    });
    await renderTeacherPanel();
    showMessage('週主題與教材已儲存。');
  } catch (error) { showError(error); }
}

async function deleteSelectedWeek(): Promise<void> {
  if (!token) return renderLogin();
  const selectedWeek = selectedTeacherWeek();
  if (!selectedWeek) return showError(new Error('請先從 Week 選單選擇已建立的 Week。'));
  const confirmed = await showConfirmModal(`確定要硬刪除 Week ${selectedWeek.week_number} — ${selectedWeek.title}？刪除後學生主畫面與班級可見週次都不會再出現。`, {
    title: '硬刪除 Week',
    confirmLabel: '硬刪除',
    danger: true
  });
  if (!confirmed) return;
  try {
    await apiFetchWithSession(`/teacher/weeks/${selectedWeek.week_id}`, { method: 'DELETE' });
    await renderTeacherPanel();
    showMessage('Week 已硬刪除。');
  } catch (error) { showError(error); }
}

async function saveTeacherClassAccess(classId: ClassId): Promise<void> {
  if (!token) return renderLogin();
  try {
    await apiFetchWithSession(`/teacher/classes/${classId}/open-weeks`, {
      method: 'PUT',
      body: JSON.stringify({ open_week_ids: checkboxValues(`teacher-open-week-${classId}`) })
    });
    teacherClassAccess[classId] = checkboxValues(`teacher-open-week-${classId}`);
    showMessage('班級可見週次已儲存。');
  } catch (error) { showError(error); }
}

getCurrentToken()
  .then((existing) => { token = existing; return token ? renderHome() : renderLogin(); })
  .catch(showError);
registerAppServiceWorker();
