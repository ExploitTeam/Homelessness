import { useEffect, useState } from "react";

import type { UserLocation } from "../types";

interface UseUserLocationResult {
  location: UserLocation | null;
  loading: boolean;
  error: string | null;
}

export function useUserLocation(): UseUserLocationResult {
  const [location, setLocation] =
    useState<UserLocation | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
  if (!navigator.geolocation) {
    setError(
      "Браузер не поддерживает определение местоположения"
    );
    setLoading(false);
    return;
  }

  const watchId = navigator.geolocation.watchPosition(
    (position) => {
      setLocation({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      });

      setLoading(false);
      setError(null);
    },

    (error) => {
      console.error(
        "Ошибка определения вашего местоположения:",
        error
      );

      setError(
        "Не удалось определить ваше местоположение"
      );

      setLoading(false);
    },

    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    }
  );

  return () => {
    navigator.geolocation.clearWatch(watchId);
  };
}, []);

  return {
    location,
    loading,
    error,
  };
}