import { useEffect, useState } from "react";

import type { Hostel, UserLocation } from "../types";
import { getHostels } from "../api/hostels";

interface UseHostelsResult {
  hostels: Hostel[];
  loading: boolean;
  error: string | null;
}

export function useHostels(
  location: UserLocation | null
): UseHostelsResult {
  const [hostels, setHostels] = useState<Hostel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (location === null) {
      setLoading(false);
      return;
    }

    const currentLocation: UserLocation = location;

    let cancelled = false;

    async function loadHostels() {
      try {
        setLoading(true);
        setError(null);

        const data = await getHostels(currentLocation);

        if (!cancelled) {
          setHostels(data);
        }
      } catch (error) {
        console.error(error);

        if (!cancelled) {
          setError("Не удалось загрузить ночлежки");
        }
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
  }, [location]);

  return {
    hostels,
    loading,
    error,
  };
}