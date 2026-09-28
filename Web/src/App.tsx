import { useCallback, useState } from "react";
import { createPortal } from "react-dom";

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

type BookingMessage = {
  type: "success" | "error";
  text: string;
};

function App() {
  const [selectedHostel, setSelectedHostel] =
    useState<Hostel | null>(null);

  const [metroRoute, setMetroRoute] =
    useState<MetroRoute | null>(null);

  const [bookedHostelIds, setBookedHostelIds] =
    useState<number[]>([]);

  const [bookingMessage, setBookingMessage] =
    useState<BookingMessage | null>(null);

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
      /*
       * Не проверяем здесь bookedHostelIds.
       *
       * Сервер должен быть источником истины.
       * Если пользователь уже забронировал эту ночлежку,
       * сервер вернет 409, и мы покажем понятную ошибку.
       */

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

        setBookingMessage({
          type: "success",
          text: "Место успешно забронировано!",
        });

        console.log("Бронь создана:", result);

        setTimeout(() => {
          setBookingMessage(null);
        }, 5000);
      } catch (error) {
        console.error(
          "Ошибка бронирования:",
          error
        );

        setBookingMessage({
          type: "error",
          text:
            error instanceof Error
              ? error.message
              : "Не удалось забронировать место. Попробуйте ещё раз.",
        });

        setTimeout(() => {
          setBookingMessage(null);
        }, 5000);
      }
    },
    []
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

      {bookingMessage &&
        createPortal(
          <div
            role="dialog"
            aria-modal="true"
            aria-live="assertive"
            style={{
              position: "fixed",

              // Занимаем весь экран
              inset: 0,

              // Максимальный z-index, чтобы уведомление
              // было поверх карты, карточки и других элементов
              zIndex: 2147483647,

              // Центрирование
              display: "flex",
              alignItems: "center",
              justifyContent: "center",

              padding: "16px",
              boxSizing: "border-box",

              // Затемняем интерфейс под сообщением
              background: "rgba(0, 0, 0, 0.32)",
            }}
          >
            <div
              style={{
                width: "100%",
                maxWidth: "420px",
                boxSizing: "border-box",

                padding: "20px",

                borderRadius: "18px",

                background:
                  bookingMessage.type === "success"
                    ? "#16a34a"
                    : "#dc2626",

                color: "#ffffff",

                boxShadow:
                  "0 18px 60px rgba(0, 0, 0, 0.45)",

                display: "flex",
                alignItems: "flex-start",
                gap: "14px",

                fontFamily: "inherit",
              }}
            >
              {/* Иконка */}
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  minWidth: "40px",

                  borderRadius: "50%",

                  background:
                    "rgba(255, 255, 255, 0.2)",

                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",

                  fontSize: "21px",
                  fontWeight: 700,
                }}
              >
                {bookingMessage.type === "success"
                  ? "✓"
                  : "!"}
              </div>

              {/* Текст */}
              <div
                style={{
                  flex: 1,
                  minWidth: 0,
                }}
              >
                <div
                  style={{
                    fontSize: "16px",
                    fontWeight: 700,
                    marginBottom: "6px",
                    lineHeight: 1.3,
                  }}
                >
                  {bookingMessage.type === "success"
                    ? "Бронирование успешно"
                    : "Не удалось забронировать"}
                </div>

                <div
                  style={{
                    fontSize: "14px",
                    lineHeight: 1.5,
                    fontWeight: 400,
                    opacity: 0.95,

                    // На случай длинного ответа
                    overflowWrap: "break-word",
                  }}
                >
                  {bookingMessage.text}
                </div>
              </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}

export default App;