import { useEffect, useState } from "react";

import { getHostels } from "../api/hostels";
import type { Hostel } from "../types";

interface UseHostelsResult {
  hostels: Hostel[];
  loading: boolean;
  error: string | null;
}

export function useHostels(): UseHostelsResult {
  const [hostels, setHostels] = useState<Hostel[]>([]);
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

        const mappedHostels: Hostel[] = data
          .filter(
            (place) =>
              place.latitude !== null &&
              place.longtitude !== null
          )
          .map((place) => ({
            id: place.id,

            lat: place.latitude as number,
            lng: place.longtitude as number,

            name:
              place.address ||
              `Пункт №${place.id}`,

            address:
              place.address ||
              "Адрес не указан",

            bedsAvailable:
              place.available_beds,

            bedsTotal:
              place.all_beds,

            openTime:
              place.open_time,

            closeTime:
              place.close_time,

            isWorking:
              Boolean(place.is_working),

            description:
              place.additional_info ?? "",

            phone: "",
            email: "",
          }));

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