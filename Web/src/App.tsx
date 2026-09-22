import { useCallback, useState } from "react";
import {
  getMaxUser,
  isRunningInsideMax,
} from "./api/max";
import MoscowMap from "./components/Map/MoscowMap";
import HostelCard from "./components/HostelCard/HostelCard";
import { useUserLocation } from "./hooks/useUserLocation";
import { useHostels } from "./hooks/useHostels";
import type { Hostel } from "./types";
import { mockUserLocation } from "./data/mockData";
import type { MetroRoute } from "./utils/metro";
import { bookHostel } from "./api/hostels";

function App() {
  const [selectedHostel, setSelectedHostel] =
    useState<Hostel | null>(null);

  const [metroRoute, setMetroRoute] =
    useState<MetroRoute | null>(null);

  const [bookedHostelIds, setBookedHostelIds] =
    useState<number[]>([]);

  const [bookingMessage, setBookingMessage] =
    useState<string | null>(null);

  const { location } = useUserLocation();

  console.log("MAX:", isRunningInsideMax());
  console.log("MAX user:", getMaxUser());
  console.log(
    "MAX initData:",
    window.WebApp?.initData
  );

  const mapLocation = location ?? mockUserLocation;

  const {
    hostels,
    loading: hostelsLoading,
    error: hostelsError,
  } = useHostels(mapLocation);

  const handleHostelClick = useCallback(
    (hostel: Hostel) => {
      setSelectedHostel(hostel);
      setMetroRoute(null);
      setBookingMessage(null);
    },
    []
  );

  const handleCloseCard = useCallback(() => {
    setSelectedHostel(null);
    setMetroRoute(null);
    setBookingMessage(null);
  }, []);

  const handleBook = useCallback(
    async (hostelId: number) => {
      if (bookedHostelIds.includes(hostelId)) {
        return;
      }

      setBookingMessage(null);

      try {
        const result = await bookHostel({
          hostelId,
          userLocation: mapLocation,
        });

        if (!result.success) {
          throw new Error(
            result.message ?? "Бронь не создана"
          );
        }

        setBookedHostelIds((current) => {
          if (current.includes(hostelId)) {
            return current;
          }

          return [...current, hostelId];
        });

        setBookingMessage(
          "Место успешно забронировано!"
        );

        console.log("Бронь создана:", result);

        setTimeout(() => {
          setBookingMessage(null);
        }, 4000);
      } catch (error) {
        console.error(
          "Ошибка бронирования:",
          error
        );

        setBookingMessage(
          "Не удалось забронировать место"
        );

        setTimeout(() => {
          setBookingMessage(null);
        }, 4000);
      }
    },
    [bookedHostelIds, mapLocation]
  );

  return (
    <div className="app">
      <MoscowMap
        hostels={hostels}
        userLocation={mapLocation}
        onHostelClick={handleHostelClick}
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

      {bookingMessage && (
        <div
          style={{
            position: "fixed",
            left: "50%",
            bottom: "24px",
            transform: "translateX(-50%)",
            zIndex: 1000,
            padding: "14px 22px",
            borderRadius: "14px",
            background:
              bookingMessage.includes("успешно")
                ? "#22c55e"
                : "#ef4444",
            color: "#fff",
            fontSize: "16px",
            fontWeight: 600,
            boxShadow:
              "0 8px 30px rgba(0, 0, 0, 0.25)",
            textAlign: "center",
          }}
        >
          {bookingMessage.includes("успешно")
            ? "✓ "
            : "⚠️ "}
          {bookingMessage}
        </div>
      )}

      {selectedHostel && (
        <HostelCard
          key={selectedHostel.id}
          hostel={selectedHostel}
          userLocation={mapLocation}
          onClose={handleCloseCard}
          onShowRoute={setMetroRoute}
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