export function renderLoading(container: HTMLElement, message = '登入中'): void {
  container.innerHTML = `
    <section class="card app-loading-card" role="status" aria-live="polite" aria-busy="true">
      <div class="app-loading-dots" aria-hidden="true">
        <span class="app-loading-dot"></span>
        <span class="app-loading-dot"></span>
        <span class="app-loading-dot"></span>
      </div>
      <h1>${escapeHtml(message)}</h1>
      <p>正在準備頁面資料，請稍候。</p>
    </section>
  `;
}

function escapeHtml(value: unknown): string {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[char]!));
}
