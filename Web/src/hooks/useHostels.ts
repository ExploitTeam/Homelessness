import { useEffect, useState } from "react";

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
    "date_time" in value
  );
}

export function useHostels(): UseHostelsResult {
  const [hostels, setHostels] = useState<HostelWithApiData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadHostels() {
      setLoading(true);
      setError(null);

      try {
        const data = await getHostels();

        if (cancelled) {
          return;
        }

        const mappedHostels = data
          .filter(
            (place) =>
              place.latitude !== null &&
              place.longtitude !== null
          )
          .map((place): HostelWithApiData => {
            const managerInfo = hasManagerInfo(
              place.manager_info
            )
              ? place.manager_info
              : null;

            const booking = hasBookingInfo(place.booking)
              ? place.booking
              : null;

            return {
              id: place.id,

              lat: place.latitude as number,
              lng: place.longtitude as number,

              name:
                place.address ||
                `Пункт №${place.id}`,

              address:
                place.address ||
                "Адрес не указан",

              bedsAvailable: place.available_beds,
              bedsTotal: place.all_beds,

              openTime: place.open_time,
              closeTime: place.close_time,

              isWorking: Boolean(place.is_working),

              description:
                place.additional_info ?? "",

              // Оставляем старые поля для совместимости
              // с остальными компонентами проекта.
              phone: managerInfo?.phone_number ?? "",
              email: "",

              // Реальные данные из /api/places.
              managerInfo,
              booking,
              homestayType: place.homestay_type,
            };
          });

        setHostels(mappedHostels);
      } catch (err) {
        if (cancelled) {
          return;
        }

        console.error(
          "Ошибка загрузки ночлежек:",
          err
        );

        setError(
          err instanceof Error
            ? err.message
            : "Не удалось загрузить ночлежки"
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadHostels();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    hostels,
    loading,
    error,
  };
}
