import { jsx as _jsx, jsxs as _jsxs } from "/releases/v5-20261019/vendor/react-vendor.mjs";
import { useCallback, useEffect, useMemo, useRef, useState, } from "/releases/v5-20261019/vendor/react-vendor.mjs";
import { createPortal } from "/releases/v5-20261019/vendor/react-vendor.mjs";

import MoscowMap from "./components/Map/MoscowMap.js";
import HostelCard from "./components/HostelCard/HostelCard.js";
import { useUserLocation } from "./hooks/useUserLocation.js";
import { useHostels } from "./hooks/useHostels.js";
import { mockUserLocation } from "./data/mockData.js";
import { bookHostel } from "./api/hostels.js";
function App() {
    const [selectedHostelId, setSelectedHostelId] = useState(null);
    const [metroRoute, setMetroRoute] = useState(null);
    const [bookedHostelIds, setBookedHostelIds] = useState([]);
    const [bookingMessage, setBookingMessage] = useState(null);
    const bookingMessageTimerRef = useRef(null);
    const { location } = useUserLocation();
    const mapLocation = location ?? mockUserLocation;
    const { hostels, loading: hostelsLoading, error: hostelsError, reload: reloadHostels, } = useHostels();
    const selectedHostel = useMemo(() => selectedHostelId === null
        ? null
        : hostels.find((hostel) => hostel.id === selectedHostelId) ?? null, [hostels, selectedHostelId]);
    useEffect(() => {
        return () => {
            if (bookingMessageTimerRef.current !== null) {
                window.clearTimeout(bookingMessageTimerRef.current);
            }
        };
    }, []);
    const showBookingMessage = useCallback((message, duration = 5000) => {
        if (bookingMessageTimerRef.current !== null) {
            window.clearTimeout(bookingMessageTimerRef.current);
        }
        setBookingMessage(message);
        bookingMessageTimerRef.current =
            window.setTimeout(() => {
                setBookingMessage(null);
                bookingMessageTimerRef.current = null;
            }, duration);
    }, []);
    const clearBookingMessage = useCallback(() => {
        if (bookingMessageTimerRef.current !== null) {
            window.clearTimeout(bookingMessageTimerRef.current);
            bookingMessageTimerRef.current = null;
        }
        setBookingMessage(null);
    }, []);
    const handleHostelClick = useCallback((hostel) => {
        setSelectedHostelId(hostel.id);
        setMetroRoute(null);
        clearBookingMessage();
    }, [clearBookingMessage]);
    const handleCloseCard = useCallback(() => {
        setSelectedHostelId(null);
        setMetroRoute(null);
        clearBookingMessage();
    }, [clearBookingMessage]);
    const handleBook = useCallback(async (hostelId) => {
        clearBookingMessage();
        try {
            const result = await bookHostel({ hostelId });
            if (!result.success) {
                throw new Error(result.message ?? "Бронь не создана");
            }
            setBookedHostelIds((current) => current.includes(hostelId)
                ? current
                : [...current, hostelId]);
            showBookingMessage({
                type: "success",
                text: "Заявка отправлена. Подтверждение появится в боте.",
            });
            /*
             * /api/places — источник истины для количества мест,
             * списка менеджеров и активной брони. После создания заявки
             * обновляем карточку без перезагрузки мини-приложения.
             */
            try {
                await reloadHostels();
            }
            catch (reloadError) {
                console.error("Не удалось обновить список после бронирования:", reloadError);
            }
        }
        catch (error) {
            console.error("Ошибка бронирования:", error);
            showBookingMessage({
                type: "error",
                text: error instanceof Error
                    ? error.message
                    : "Не удалось забронировать место. Попробуйте ещё раз.",
            });
        }
    }, [clearBookingMessage, reloadHostels, showBookingMessage]);
    return (_jsxs("div", { className: "app", children: [_jsx("span", { className: "app-release", "aria-label": "\u0412\u0435\u0440\u0441\u0438\u044F \u0438\u043D\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430 v5", children: "v5" }), _jsx(MoscowMap, { hostels: hostels, userLocation: mapLocation, onHostelClick: handleHostelClick, route: metroRoute, selectedHostel: selectedHostel }), hostelsLoading && hostels.length === 0 && (_jsx("div", { className: "map-status", children: "\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u0435\u043C \u043F\u0443\u043D\u043A\u0442\u044B..." })), hostelsError && (_jsx("div", { className: "map-error", children: hostelsError })), selectedHostel && (_jsx(HostelCard, { hostel: selectedHostel, userLocation: mapLocation, onClose: handleCloseCard, onShowRoute: setMetroRoute, booked: bookedHostelIds.includes(selectedHostel.id), onBook: handleBook }, selectedHostel.id)), bookingMessage &&
                createPortal(_jsx("div", { role: "alertdialog", "aria-live": "assertive", className: "booking-notice-overlay", onClick: clearBookingMessage, children: _jsxs("div", { className: `booking-notice booking-notice--${bookingMessage.type}`, onClick: (event) => event.stopPropagation(), children: [_jsx("div", { className: "booking-notice__icon", children: bookingMessage.type === "success"
                                    ? "✓"
                                    : "!" }), _jsxs("div", { className: "booking-notice__body", children: [_jsx("div", { className: "booking-notice__title", children: bookingMessage.type === "success"
                                            ? "Бронирование успешно"
                                            : "Не удалось забронировать" }), _jsx("div", { className: "booking-notice__text", children: bookingMessage.text })] }), _jsx("button", { type: "button", className: "booking-notice__close", onClick: clearBookingMessage, "aria-label": "\u0417\u0430\u043A\u0440\u044B\u0442\u044C \u0443\u0432\u0435\u0434\u043E\u043C\u043B\u0435\u043D\u0438\u0435", children: "\u00D7" })] }) }), document.body)] }));
}
export default App;
