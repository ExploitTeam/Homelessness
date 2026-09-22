import { useEffect, useState } from "react";

import { getHostels } from "../api/hostels";

import type { Hostel, UserLocation } from "../types";

interface UseHostelsResult {
  hostels: Hostel[];
  loading: boolean;
  error: string | null;
}

interface BackendCoordinates {
  lat?: number | null;
  lng?: number | null;
  latitude?: number | null;
  longitude?: number | null;
}

const demoCoordinates: Record<
  number,
  { lat: number; lng: number }
> = {
  1: {
    lat: 55.7558,
    lng: 37.6176,
  },
  2: {
    lat: 55.7887,
    lng: 37.6767,
  },
  3: {
    lat: 55.8311,
    lng: 37.385,
  },
};

const fallbackCoordinates = {
  lat: 55.751244,
  lng: 37.618423,
};

function getCoordinates(
  place: BackendCoordinates & { id: number }
) {
  const backendLat =
    place.lat ?? place.latitude;

  const backendLng =
    place.lng ?? place.longitude;

  if (
    typeof backendLat === "number" &&
    typeof backendLng === "number"
  ) {
    return {
      lat: backendLat,
      lng: backendLng,
    };
  }

  return (
    demoCoordinates[place.id] ??
    fallbackCoordinates
  );
}

export function useHostels(
  userLocation: UserLocation | null
): UseHostelsResult {
  const [hostels, setHostels] =
    useState<Hostel[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadHostels() {
      setLoading(true);
      setError(null);

      try {
        const data =
          await getHostels(
            userLocation ?? undefined
          );

        if (cancelled) {
          return;
        }

        const mappedHostels: Hostel[] =
          data.map((place) => {
            const coordinates =
              getCoordinates(place);

            return {
              id: place.id,

              lat: coordinates.lat,
              lng: coordinates.lng,

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

              description:
                place.additional_info || "",

              phone: "",
              email: "",

              openTime:
                place.open_time || "",

              closeTime:
                place.close_time || "",

              isWorking:
                Boolean(place.is_working),
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
  }, [userLocation]);

  return {
    hostels,
    loading,
    error,
  };
}