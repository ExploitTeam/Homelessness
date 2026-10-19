import { useCallback, useEffect, useRef, useState, } from "/releases/v5-20261019/vendor/react-vendor.mjs";
import { getHostels, } from "../api/hostels.js";
function hasManagerInfo(value) {
    return (typeof value === "object" &&
        value !== null &&
        "username" in value &&
        "phone_number" in value);
}
function hasBookingInfo(value) {
    return (typeof value === "object" &&
        value !== null &&
        "id" in value &&
        "user_id" in value &&
        "homestay_id" in value &&
        "date_time" in value &&
        "is_approved" in value);
}
function mapBackendPlace(place) {
    const managerInfo = hasManagerInfo(place.manager_info)
        ? place.manager_info
        : null;
    const booking = hasBookingInfo(place.booking)
        ? place.booking
        : null;
    const managers = Array.isArray(place.managers)
        ? place.managers.filter((manager) => typeof manager.name === "string")
        : managerInfo
            ? [{ name: managerInfo.username || "Сотрудник пункта", phone: managerInfo.phone_number || null }]
            : [];
    const categoryLabel = place.category_label?.trim() || "Пункт помощи";
    return {
        id: place.id,
        lat: place.latitude,
        lng: place.longtitude,
        name: categoryLabel,
        address: place.address || "Адрес не указан",
        bedsAvailable: place.available_beds,
        bedsTotal: place.all_beds,
        openTime: place.open_time,
        closeTime: place.close_time,
        isWorking: Boolean(place.is_working),
        description: place.additional_info ?? "",
        // Старые поля сохраняем для совместимости со старым UI.
        phone: managers[0]?.phone ?? "",
        email: "",
        // Реальные данные из /api/places.
        managerInfo,
        managers,
        fund: place.fund ?? null,
        categoryLabel,
        booking,
        homestayType: place.homestay_type,
    };
}
export function useHostels() {
    const [hostels, setHostels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const mountedRef = useRef(false);
    const requestIdRef = useRef(0);
    const reload = useCallback(async () => {
        const requestId = ++requestIdRef.current;
        if (mountedRef.current) {
            setLoading(true);
            setError(null);
        }
        try {
            const data = await getHostels();
            if (!mountedRef.current ||
                requestId !== requestIdRef.current) {
                return;
            }
            const mappedHostels = data
                .filter((place) => place.latitude !== null &&
                place.longtitude !== null &&
                Number.isFinite(place.latitude) &&
                Number.isFinite(place.longtitude))
                .map(mapBackendPlace);
            setHostels(mappedHostels);
        }
        catch (err) {
            if (!mountedRef.current ||
                requestId !== requestIdRef.current) {
                return;
            }
            console.error("Ошибка загрузки пунктов помощи:", err);
            setError(err instanceof Error
                ? err.message
                : "Не удалось загрузить пункты помощи");
        }
        finally {
            if (mountedRef.current &&
                requestId === requestIdRef.current) {
                setLoading(false);
            }
        }
    }, []);
    useEffect(() => {
        mountedRef.current = true;
        void reload();
        return () => {
            mountedRef.current = false;
            requestIdRef.current += 1;
        };
    }, [reload]);
    return {
        hostels,
        loading,
        error,
        reload,
    };
}
