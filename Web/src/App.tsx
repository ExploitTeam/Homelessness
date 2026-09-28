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
  } = useHostels();

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
        }, 5000);
      } catch (error) {
        console.error(
          "Ошибка бронирования:",
          error
        );

        setBookingMessage(
          error instanceof Error
            ? error.message
            : "Не удалось забронировать место"
        );

        setTimeout(() => {
          setBookingMessage(null);
        }, 4000);
      }
    },
    [bookedHostelIds]
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
            top: "20px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 999999,
            width: "calc(100% - 32px)",
            maxWidth: "420px",
            boxSizing: "border-box",
            padding: "16px 18px",
            borderRadius: "16px",
            background: bookingMessage.includes("успешно")
              ? "#16a34a"
              : "#dc2626",
            color: "#ffffff",
            boxShadow:
              "0 10px 35px rgba(0, 0, 0, 0.28)",
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
            fontFamily: "inherit",
          }}
        >
          <div
            style={{
              width: "34px",
              height: "34px",
              minWidth: "34px",
              borderRadius: "50%",
              background: "rgba(255, 255, 255, 0.18)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "18px",
            }}
          >
            {bookingMessage.includes("успешно") ? "✓" : "!"}
          </div>

          <div
            style={{
              flex: 1,
              minWidth: 0,
            }}
          >
            <div
              style={{
                fontSize: "15px",
                fontWeight: 700,
                marginBottom: "4px",
              }}
            >
              {bookingMessage.includes("успешно")
                ? "Бронирование успешно"
                : "Не удалось забронировать"}
            </div>

            <div
              style={{
                fontSize: "14px",
                lineHeight: 1.45,
                fontWeight: 400,
                opacity: 0.95,
              }}
            >
              {bookingMessage}
            </div>
          </div>
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