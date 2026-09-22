import {
  useCallback,
  useState,
} from "react";

import MoscowMap from "./components/Map/MoscowMap";
import HostelCard from "./components/HostelCard/HostelCard";

import { useUserLocation } from "./hooks/useUserLocation";
import { useHostels } from "./hooks/useHostels";

import type { Hostel } from "./types";

import { mockUserLocation } from "./data/mockData";

import type { MetroRoute } from "./utils/metro";

import { bookHostel } from "./api/hostels";

function App() {
  const [
    selectedHostel,
    setSelectedHostel,
  ] = useState<Hostel | null>(null);

  const [
    metroRoute,
    setMetroRoute,
  ] = useState<MetroRoute | null>(null);

  const [
    bookedHostelIds,
    setBookedHostelIds,
  ] = useState<number[]>([]);

  const { location } =
    useUserLocation();

  const mapLocation =
    location ?? mockUserLocation;

  const {
    hostels,
    loading: hostelsLoading,
    error: hostelsError,
  } = useHostels(mapLocation);

  /*
   * =========================
   * ВЫБОР НОЧЛЕЖКИ
   * =========================
   */

  const handleHostelClick =
    useCallback(
      (hostel: Hostel) => {
        setSelectedHostel(hostel);
        setMetroRoute(null);
      },
      []
    );

  /*
   * =========================
   * ЗАКРЫТИЕ КАРТОЧКИ
   * =========================
   */

  const handleCloseCard =
    useCallback(() => {
      setSelectedHostel(null);
      setMetroRoute(null);
    }, []);

  /*
   * =========================
   * БРОНИРОВАНИЕ
   * =========================
   */

  const handleBook =
    useCallback(
      async (hostelId: number) => {
        /*
         * Если именно эта ночлежка
         * уже забронирована —
         * ничего не делаем.
         */

        if (
          bookedHostelIds.includes(
            hostelId
          )
        ) {
          return;
        }

        try {
          const result =
            await bookHostel({
              hostelId,
              userLocation:
                mapLocation,
            });

          if (!result.success) {
            throw new Error(
              result.message ??
                "Бронь не создана"
            );
          }

          /*
           * Добавляем только ID
           * конкретной ночлежки.
           */

          setBookedHostelIds(
            (current) => {
              if (
                current.includes(
                  hostelId
                )
              ) {
                return current;
              }

              return [
                ...current,
                hostelId,
              ];
            }
          );

          console.log(
            "Бронь создана:",
            result
          );
        } catch (error) {
          console.error(
            "Ошибка бронирования:",
            error
          );

          alert(
            "Не удалось забронировать место"
          );
        }
      },
      [
        bookedHostelIds,
        mapLocation,
      ]
    );

  return (
    <div className="app">
      <MoscowMap
        hostels={hostels}
        userLocation={mapLocation}
        onHostelClick={
          handleHostelClick
        }
        route={metroRoute}
      />

      {hostelsLoading && (
        <div className="map-status">
          Загружаем ночлежки...
        </div>
      )}

      {hostelsError && (
        <div className="map-error">
          {hostelsError}
        </div>
      )}

      {selectedHostel && (
        <HostelCard
          key={selectedHostel.id}
          hostel={selectedHostel}
          userLocation={mapLocation}
          onClose={handleCloseCard}
          onShowRoute={
            setMetroRoute
          }
          booked={bookedHostelIds.includes(
            selectedHostel.id
          )}
          onBook={handleBook}
        />
      )}
    </div>
  );
}

export default App;