export function getMaxInitData(): string {
  return window.WebApp?.initData ?? "";
}

export function getMaxUserId(): number | null {
  return (
    window.WebApp?.initDataUnsafe?.user?.id ??
    null
  );
}

export function getMaxUser() {
  return window.WebApp?.initDataUnsafe?.user ?? null;
}

export function isRunningInsideMax(): boolean {
  return Boolean(window.WebApp);
}