export interface ResponseModalOptions {
  title?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

let activeCleanup: (() => void) | null = null;

function closeActiveModal(): void {
  activeCleanup?.();
  activeCleanup = null;
}

function buildModal(title: string, message: string, options: ResponseModalOptions): {
  backdrop: HTMLDivElement;
  confirmButton: HTMLButtonElement;
  cancelButton: HTMLButtonElement | null;
  cleanup: () => void;
} {
  closeActiveModal();
  const backdrop = document.createElement('div');
  backdrop.className = 'app-modal-backdrop';
  backdrop.innerHTML = `
    <div class="app-modal-card" role="dialog" aria-modal="true" aria-labelledby="app-modal-title" aria-describedby="app-modal-message">
      <h2 id="app-modal-title"></h2>
      <p id="app-modal-message" class="app-modal-message"></p>
      <div class="app-modal-actions"></div>
    </div>
  `;

  const titleElement = backdrop.querySelector<HTMLHeadingElement>('#app-modal-title')!;
  const messageElement = backdrop.querySelector<HTMLParagraphElement>('#app-modal-message')!;
  const actions = backdrop.querySelector<HTMLDivElement>('.app-modal-actions')!;
  titleElement.textContent = title;
  messageElement.textContent = message;

  const cancelButton = options.cancelLabel ? document.createElement('button') : null;
  if (cancelButton) {
    cancelButton.type = 'button';
    cancelButton.className = 'secondary';
    cancelButton.textContent = options.cancelLabel ?? '取消';
    actions.append(cancelButton);
  }

  const confirmButton = document.createElement('button');
  confirmButton.type = 'button';
  confirmButton.className = options.danger ? 'danger' : '';
  confirmButton.textContent = options.confirmLabel ?? '知道了';
  actions.append(confirmButton);

  const previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const cleanup = () => {
    backdrop.remove();
    document.removeEventListener('keydown', handleEscape);
    previousActiveElement?.focus();
  };
  const handleEscape = (event: KeyboardEvent) => {
    if (event.key === 'Escape') (cancelButton ?? confirmButton).click();
  };

  document.addEventListener('keydown', handleEscape);
  document.body.append(backdrop);
  activeCleanup = cleanup;
  queueMicrotask(() => confirmButton.focus());
  return { backdrop, confirmButton, cancelButton, cleanup };
}

export function showResponseModal(message: string, options: ResponseModalOptions = {}): Promise<void> {
  return new Promise((resolve) => {
    const { confirmButton, cleanup } = buildModal(options.title ?? '提示', message, options);
    confirmButton.addEventListener('click', () => {
      cleanup();
      activeCleanup = null;
      resolve();
    }, { once: true });
  });
}

export function showConfirmModal(message: string, options: ResponseModalOptions = {}): Promise<boolean> {
  return new Promise((resolve) => {
    const { backdrop, confirmButton, cancelButton, cleanup } = buildModal(options.title ?? '確認操作', message, {
      ...options,
      confirmLabel: options.confirmLabel ?? '確認',
      cancelLabel: options.cancelLabel ?? '取消'
    });
    const finish = (result: boolean) => {
      cleanup();
      activeCleanup = null;
      resolve(result);
    };
    confirmButton.addEventListener('click', () => finish(true), { once: true });
    cancelButton?.addEventListener('click', () => finish(false), { once: true });
    backdrop.addEventListener('click', (event) => {
      if (event.target === backdrop) finish(false);
    });
  });
}
