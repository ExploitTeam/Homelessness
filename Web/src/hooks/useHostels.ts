import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getHostels,
  type BackendPlace,
  type BookingInfo,
  type ManagerInfo,
} from "../api/hostels";
import type { Hostel } from "../types";

export type HostelWithApiData = Hostel & {
  managerInfo: ManagerInfo | null;
  booking: BookingInfo | null;
  homestayType: number;
};

interface UseHostelsResult {
  hostels: HostelWithApiData[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

function hasManagerInfo(
  value: BackendPlace["manager_info"]
): value is ManagerInfo {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    "username" in value &&
    "phone_number" in value
  );
}

function hasBookingInfo(
  value: BackendPlace["booking"]
): value is BookingInfo {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    "user_id" in value &&
    "homestay_id" in value &&
    "date_time" in value &&
    "is_approved" in value
  );
}

function mapBackendPlace(
  place: BackendPlace
): HostelWithApiData {
  const managerInfo = hasManagerInfo(place.manager_info)
    ? place.manager_info
    : null;

  const booking = hasBookingInfo(place.booking)
    ? place.booking
    : null;

  return {
    id: place.id,

    lat: place.latitude as number,
    lng: place.longtitude as number,

    name: place.address || `Пункт №${place.id}`,
    address: place.address || "Адрес не указан",

    bedsAvailable: place.available_beds,
    bedsTotal: place.all_beds,

    openTime: place.open_time,
    closeTime: place.close_time,

    isWorking: Boolean(place.is_working),

    description: place.additional_info ?? "",

    // Старые поля сохраняем для совместимости со старым UI.
    phone: managerInfo?.phone_number ?? "",
    email: "",

    // Реальные данные из /api/places.
    managerInfo,
    booking,
    homestayType: place.homestay_type,
  };
}

export function useHostels(): UseHostelsResult {
  const [hostels, setHostels] =
    useState<HostelWithApiData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

      if (
        !mountedRef.current ||
        requestId !== requestIdRef.current
      ) {
        return;
      }

      const mappedHostels = data
        .filter(
          (place) =>
            place.latitude !== null &&
            place.longtitude !== null &&
            Number.isFinite(place.latitude) &&
            Number.isFinite(place.longtitude)
        )
        .map(mapBackendPlace);

      setHostels(mappedHostels);
    } catch (err) {
      if (
        !mountedRef.current ||
        requestId !== requestIdRef.current
      ) {
        return;
      }

      console.error("Ошибка загрузки ночлежек:", err);

      setError(
        err instanceof Error
          ? err.message
          : "Не удалось загрузить ночлежки"
      );
    } finally {
      if (
        mountedRef.current &&
        requestId === requestIdRef.current
      ) {
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
