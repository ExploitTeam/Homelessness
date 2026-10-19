import { jsx as _jsx, jsxs as _jsxs } from "/releases/v5-20261019/vendor/react-vendor.mjs";
import { useEffect, useRef, useState } from "/releases/v5-20261019/vendor/react-vendor.mjs";
import { findMetroRoute, getNearestMetro, getWalkingTime } from "../../utils/metro.js";
function distanceKm(a, b) {
    const toRad = (n) => (n * Math.PI) / 180;
    const deltaLat = toRad(b.lat - a.lat);
    const deltaLng = toRad(b.lng - a.lng);
    const x = Math.sin(deltaLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(deltaLng / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}
function formatDistance(value) {
    return value < 1 ? `${Math.round(value * 1000)} м` : `${value.toFixed(1).replace(".", ",")} км`;
}
function formatDate(value) {
    const date = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(value);
    return date ? `${date[3]}.${date[2]}.${date[1]} в ${date[4]}:${date[5]}` : value || "Не указана";
}
function bookingStatus(value) {
    return value === 1 ? "Подтверждено" : "Ожидает подтверждения";
}
function getSchedule(open, close) {
    if (!open || !close)
        return null;
    if (open.slice(0, 5) === close.slice(0, 5))
        return "Круглосуточно";
    return `${open.slice(0, 5)}–${close.slice(0, 5)}`;
}
export default function HostelCard({ hostel, userLocation, onClose, onShowRoute, booked, onBook }) {
    const cardRef = useRef(null);
    const scrollRef = useRef(null);
    const contactsRef = useRef(null);
    const dragRef = useRef(null);
    const suppressClickRef = useRef(false);
    const [collapsed, setCollapsed] = useState(false);
    const [dragOffset, setDragOffset] = useState(null);
    const [dragging, setDragging] = useState(false);
    const [saving, setSaving] = useState(false);
    const [showRoute, setShowRoute] = useState(false);
    const isBooked = booked || hostel.booking !== null;
    const canBook = !isBooked && hostel.bedsAvailable > 0;
    const schedule = getSchedule(hostel.openTime || "", hostel.closeTime || "");
    const distance = distanceKm(userLocation, { lat: hostel.lat, lng: hostel.lng });
    const pointMetro = getNearestMetro(hostel.lat, hostel.lng);
    const userMetro = getNearestMetro(userLocation.lat, userLocation.lng);
    const metroAvailable = distanceKm(userLocation, { lat: userMetro.lat, lng: userMetro.lng }) <= 20 &&
        distanceKm({ lat: hostel.lat, lng: hostel.lng }, { lat: pointMetro.lat, lng: pointMetro.lng }) <= 20;
    const metroRoute = metroAvailable ? findMetroRoute(userMetro, pointMetro) : null;
    useEffect(() => {
        setCollapsed(false);
        setDragOffset(null);
        setShowRoute(false);
        onShowRoute(null);
        scrollRef.current?.scrollTo({ top: 0 });
    }, [hostel.id, onShowRoute]);
    function openContacts() {
        setCollapsed(false);
        const scroll = scrollRef.current;
        const target = contactsRef.current;
        if (!scroll || !target)
            return;
        const top = target.getBoundingClientRect().top - scroll.getBoundingClientRect().top + scroll.scrollTop - 14;
        scroll.scrollTo({ top, behavior: "smooth" });
    }
    async function submitBooking() {
        if (!canBook || saving)
            return;
        setSaving(true);
        try {
            await onBook(hostel.id);
        }
        finally {
            setSaving(false);
        }
    }
    function toggleRoute() {
        if (!metroRoute)
            return;
        const next = !showRoute;
        setShowRoute(next);
        onShowRoute(next ? metroRoute : null);
        if (next)
            setCollapsed(true);
    }
    // Двигается только специальная верхняя ручка; прокрутка текста, контактов
    // и нажатия на нижние кнопки не конфликтуют с перемещением карточки.
    function beginDrag(clientY, mode) {
        const height = cardRef.current?.getBoundingClientRect().height ?? 0;
        const maxOffset = Math.max(0, height - 108);
        const startOffset = collapsed ? maxOffset : 0;
        dragRef.current = { startY: clientY, startOffset, currentOffset: startOffset, maxOffset, mode };
        setDragOffset(startOffset);
        setDragging(true);
    }
    useEffect(() => {
        function move(clientY) {
            const drag = dragRef.current;
            if (!drag)
                return;
            drag.currentOffset = Math.min(drag.maxOffset, Math.max(0, drag.startOffset + clientY - drag.startY));
            setDragOffset(drag.currentOffset);
        }
        function finish(clientY) {
            const drag = dragRef.current;
            if (!drag)
                return;
            dragRef.current = null;
            setDragging(false);
            setDragOffset(null);
            const delta = clientY - drag.startY;
            setCollapsed(Math.abs(delta) < 10 ? !collapsed : delta > 45 || (delta >= -45 && drag.currentOffset > drag.maxOffset / 2));
            suppressClickRef.current = true;
            window.setTimeout(() => { suppressClickRef.current = false; }, 350);
        }
        const onMouseMove = (event) => {
            if (dragRef.current?.mode !== "mouse")
                return;
            event.preventDefault();
            move(event.clientY);
        };
        const onMouseUp = (event) => {
            if (dragRef.current?.mode === "mouse")
                finish(event.clientY);
        };
        const onTouchMove = (event) => {
            if (dragRef.current?.mode !== "touch")
                return;
            const touch = event.touches[0];
            if (touch) {
                event.preventDefault();
                move(touch.clientY);
            }
        };
        const onTouchEnd = (event) => {
            if (dragRef.current?.mode === "touch")
                finish(event.changedTouches[0]?.clientY ?? dragRef.current.startY);
        };
        window.addEventListener("mousemove", onMouseMove, { passive: false });
        window.addEventListener("mouseup", onMouseUp);
        window.addEventListener("touchmove", onTouchMove, { passive: false });
        window.addEventListener("touchend", onTouchEnd);
        window.addEventListener("touchcancel", onTouchEnd);
        return () => {
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
            window.removeEventListener("touchmove", onTouchMove);
            window.removeEventListener("touchend", onTouchEnd);
            window.removeEventListener("touchcancel", onTouchEnd);
        };
    }, [collapsed]);
    function dragMouseDown(event) {
        if (event.button !== 0)
            return;
        event.preventDefault();
        beginDrag(event.clientY, "mouse");
    }
    function dragTouchStart(event) {
        if (event.touches[0])
            beginDrag(event.touches[0].clientY, "touch");
    }
    return (_jsxs("article", { ref: cardRef, className: `place-sheet${collapsed ? " place-sheet--collapsed" : ""}${dragging ? " place-sheet--dragging" : ""}`, style: dragOffset === null ? undefined : { transform: `translate3d(-50%, ${dragOffset}px, 0)` }, "aria-label": `Информация о пункте: ${hostel.address}`, children: [_jsx("button", { type: "button", className: "place-sheet__handle-control", "aria-label": collapsed ? "Развернуть карточку пункта" : "Свернуть карточку пункта", "aria-expanded": !collapsed, onMouseDown: dragMouseDown, onTouchStart: dragTouchStart, onClick: () => {
                    if (!suppressClickRef.current)
                        setCollapsed((current) => !current);
                }, children: _jsx("span", { className: "place-sheet__handle", "aria-hidden": "true" }) }), _jsxs("div", { className: "place-sheet__topline", children: [_jsxs("div", { className: "place-sheet__heading", children: [_jsx("span", { className: "place-sheet__eyebrow", children: "\u041F\u0423\u041D\u041A\u0422 \u041F\u041E\u041C\u041E\u0429\u0418" }), _jsx("h2", { children: hostel.categoryLabel }), _jsxs("p", { children: ["\uD83D\uDCCD ", hostel.address] })] }), _jsx("button", { type: "button", className: "place-sheet__close", onClick: onClose, "aria-label": "\u0417\u0430\u043A\u0440\u044B\u0442\u044C \u043A\u0430\u0440\u0442\u043E\u0447\u043A\u0443", children: "\u00D7" })] }), _jsxs("div", { ref: scrollRef, className: "place-sheet__scroll", children: [_jsxs("div", { className: "place-sheet__overview", children: [_jsxs("div", { className: `place-sheet__status${hostel.isWorking ? " place-sheet__status--active" : ""}`, children: [_jsx("span", { "aria-hidden": "true", children: "\u25CF" }), hostel.isWorking ? "Пункт работает" : "Пункт временно не работает"] }), _jsxs("div", { className: "place-sheet__facts", children: [_jsxs("div", { children: [_jsx("span", { className: "place-sheet__fact-icon", children: "\u2197" }), _jsx("small", { children: "\u0420\u0430\u0441\u0441\u0442\u043E\u044F\u043D\u0438\u0435 \u043F\u043E \u043F\u0440\u044F\u043C\u043E\u0439" }), _jsx("strong", { children: formatDistance(distance) })] }), _jsxs("div", { children: [_jsx("span", { className: "place-sheet__fact-icon", children: "\uD83D\uDECF\uFE0F" }), _jsx("small", { children: "\u0421\u0432\u043E\u0431\u043E\u0434\u043D\u044B\u0445 \u043C\u0435\u0441\u0442" }), _jsx("strong", { children: hostel.bedsTotal > 0 ? `${hostel.bedsAvailable} из ${hostel.bedsTotal}` : "Не указано" })] }), _jsxs("div", { children: [_jsx("span", { className: "place-sheet__fact-icon", children: "\uD83D\uDD52" }), _jsx("small", { children: "\u0412\u0440\u0435\u043C\u044F \u0440\u0430\u0431\u043E\u0442\u044B" }), _jsx("strong", { children: schedule ?? "Уточняйте" })] })] })] }), _jsxs("section", { className: "place-sheet__section place-sheet__fund", "aria-labelledby": "place-fund-title", children: [_jsxs("div", { className: "place-sheet__section-title", children: [_jsx("span", { "aria-hidden": "true", children: "\uD83E\uDD1D" }), _jsx("h3", { id: "place-fund-title", children: "\u041E\u0440\u0433\u0430\u043D\u0438\u0437\u0430\u0446\u0438\u044F" })] }), _jsxs("div", { className: "place-sheet__fund-content", children: [_jsx("span", { className: "place-sheet__meta-label", children: "\u0411\u043B\u0430\u0433\u043E\u0442\u0432\u043E\u0440\u0438\u0442\u0435\u043B\u044C\u043D\u044B\u0439 \u0444\u043E\u043D\u0434" }), _jsx("strong", { className: "place-sheet__fund-name", children: hostel.fund?.name || "Фонд не указан" }), hostel.fund?.description ? (_jsx("p", { className: "place-sheet__description", children: hostel.fund.description })) : (_jsx("p", { className: "place-sheet__muted", children: "\u041E\u043F\u0438\u0441\u0430\u043D\u0438\u0435 \u0444\u043E\u043D\u0434\u0430 \u043F\u043E\u043A\u0430 \u043D\u0435 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D\u043E." }))] })] }), _jsxs("section", { className: "place-sheet__section", "aria-labelledby": "place-about-title", children: [_jsxs("div", { className: "place-sheet__section-title", children: [_jsx("span", { "aria-hidden": "true", children: "\uD83D\uDCCB" }), _jsx("h3", { id: "place-about-title", children: "\u041E \u043F\u0443\u043D\u043A\u0442\u0435" })] }), _jsx("p", { className: hostel.description ? "place-sheet__description" : "place-sheet__muted", children: hostel.description || "Дополнительная информация о пункте пока не указана." })] }), hostel.booking && (_jsxs("section", { className: "place-sheet__section place-sheet__booking", "aria-labelledby": "place-booking-title", children: [_jsxs("div", { className: "place-sheet__section-title", children: [_jsx("span", { "aria-hidden": "true", children: "\uD83C\uDF9F\uFE0F" }), _jsx("h3", { id: "place-booking-title", children: "\u041C\u043E\u044F \u0431\u0440\u043E\u043D\u044C" })] }), _jsx("p", { className: "place-sheet__booking-status", children: bookingStatus(hostel.booking.is_approved) }), _jsxs("p", { children: ["\u0417\u0430\u044F\u0432\u043A\u0430 \u2116", hostel.booking.id, " \u00B7 ", formatDate(hostel.booking.date_time)] })] })), _jsxs("section", { ref: contactsRef, className: "place-sheet__section place-sheet__contacts", "aria-labelledby": "place-contacts-title", children: [_jsxs("div", { className: "place-sheet__section-title", children: [_jsx("span", { "aria-hidden": "true", children: "\u260E\uFE0F" }), _jsx("h3", { id: "place-contacts-title", children: "\u041A\u043E\u043D\u0442\u0430\u043A\u0442\u044B \u043F\u0443\u043D\u043A\u0442\u0430" })] }), hostel.managers.length === 0 ? (_jsx("p", { className: "place-sheet__muted", children: "\u041A\u043E\u043D\u0442\u0430\u043A\u0442\u043D\u044B\u0435 \u043B\u0438\u0446\u0430 \u043F\u043E\u043A\u0430 \u043D\u0435 \u0443\u043A\u0430\u0437\u0430\u043D\u044B." })) : (_jsx("div", { className: "place-sheet__managers", children: hostel.managers.map((manager, index) => (_jsxs("div", { className: "place-sheet__manager", children: [_jsx("div", { className: "place-sheet__manager-avatar", "aria-hidden": "true", children: "\uD83D\uDC64" }), _jsxs("div", { className: "place-sheet__manager-details", children: [_jsx("strong", { children: manager.name || "Сотрудник пункта" }), _jsx("span", { children: "\u041A\u043E\u043D\u0442\u0430\u043A\u0442\u043D\u043E\u0435 \u043B\u0438\u0446\u043E" }), manager.phone ? (_jsxs("a", { href: `tel:${manager.phone.replace(/[^\d+]/g, "")}`, children: ["\uD83D\uDCDE ", manager.phone] })) : (_jsx("small", { children: "\u041D\u043E\u043C\u0435\u0440 \u0442\u0435\u043B\u0435\u0444\u043E\u043D\u0430 \u043D\u0435 \u0443\u043A\u0430\u0437\u0430\u043D" }))] })] }, `${index}-${manager.name}`))) }))] }), _jsxs("section", { className: "place-sheet__section", "aria-labelledby": "place-route-title", children: [_jsxs("div", { className: "place-sheet__section-title", children: [_jsx("span", { "aria-hidden": "true", children: "\uD83D\uDDFA\uFE0F" }), _jsx("h3", { id: "place-route-title", children: "\u041A\u0430\u043A \u0434\u043E\u0431\u0440\u0430\u0442\u044C\u0441\u044F" })] }), _jsxs("details", { className: "place-sheet__route-details", children: [_jsxs("summary", { children: ["\u041C\u0430\u0440\u0448\u0440\u0443\u0442 \u043D\u0430 \u043C\u0435\u0442\u0440\u043E ", _jsx("span", { "aria-hidden": "true", children: "\u2304" })] }), metroAvailable && metroRoute ? (_jsxs("div", { className: "place-sheet__route-content", children: [_jsxs("p", { children: [_jsx("strong", { children: "\u041E\u0442:" }), " ", userMetro.name, " ", _jsxs("small", { children: ["(", getWalkingTime(userLocation.lat, userLocation.lng, userMetro), " \u043C\u0438\u043D \u043F\u0435\u0448\u043A\u043E\u043C \u0434\u043E \u0441\u0442\u0430\u043D\u0446\u0438\u0438)"] })] }), _jsxs("p", { children: [_jsx("strong", { children: "\u0414\u043E:" }), " ", pointMetro.name, " ", _jsxs("small", { children: ["(", getWalkingTime(hostel.lat, hostel.lng, pointMetro), " \u043C\u0438\u043D \u043F\u0435\u0448\u043A\u043E\u043C \u0434\u043E \u043F\u0443\u043D\u043A\u0442\u0430)"] })] }), _jsx("button", { type: "button", className: "place-sheet__route-button", onClick: toggleRoute, children: showRoute ? "Скрыть маршрут с карты" : "Показать на карте" })] })) : _jsx("p", { className: "place-sheet__muted", children: "\u041C\u0430\u0440\u0448\u0440\u0443\u0442 \u041C\u043E\u0441\u043A\u043E\u0432\u0441\u043A\u043E\u0433\u043E \u043C\u0435\u0442\u0440\u043E \u0434\u043B\u044F \u044D\u0442\u043E\u0433\u043E \u043F\u0443\u043D\u043A\u0442\u0430 \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u0435\u043D." })] })] })] }), _jsxs("footer", { className: "place-sheet__actions", "aria-label": "\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u044F \u0441 \u043F\u0443\u043D\u043A\u0442\u043E\u043C", children: [_jsx("button", { type: "button", className: "place-sheet__contact-button", onClick: openContacts, children: "\u260E\uFE0F \u041A\u043E\u043D\u0442\u0430\u043A\u0442\u044B" }), _jsx("button", { type: "button", className: `place-sheet__book-button${isBooked ? " place-sheet__book-button--booked" : ""}`, disabled: saving || !canBook, onClick: submitBooking, children: saving ? "Отправляем…" : isBooked ? "✓ Заявка подана" : hostel.bedsAvailable <= 0 ? "Нет мест" : "Забронировать" })] })] }));
}
