export function getMaxInitData() {
    return window.WebApp?.initData ?? "";
}
export function getMaxUserId() {
    return (window.WebApp?.initDataUnsafe?.user?.id ??
        null);
}
export function getMaxUser() {
    return window.WebApp?.initDataUnsafe?.user ?? null;
}
export function isRunningInsideMax() {
    return Boolean(window.WebApp);
}
