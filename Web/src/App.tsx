import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

import "./App.css";

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
  const [selectedHostelId, setSelectedHostelId] =
    useState<number | null>(null);

  const [metroRoute, setMetroRoute] =
    useState<MetroRoute | null>(null);

  const [bookedHostelIds, setBookedHostelIds] =
    useState<number[]>([]);

  const [bookingMessage, setBookingMessage] =
    useState<BookingMessage | null>(null);

  const bookingMessageTimerRef =
    useRef<number | null>(null);

  const { location } = useUserLocation();
  const mapLocation = location ?? mockUserLocation;

  const {
    hostels,
    loading: hostelsLoading,
    error: hostelsError,
    reload: reloadHostels,
  } = useHostels();

  const selectedHostel = useMemo(
    () =>
      selectedHostelId === null
        ? null
        : hostels.find(
            (hostel) => hostel.id === selectedHostelId
          ) ?? null,
    [hostels, selectedHostelId]
  );

  useEffect(() => {
    console.log("MAX:", isRunningInsideMax());
    console.log("MAX user:", getMaxUser());
    console.log("MAX initData:", window.WebApp?.initData);
  }, []);

  useEffect(() => {
    return () => {
      if (bookingMessageTimerRef.current !== null) {
        window.clearTimeout(
          bookingMessageTimerRef.current
        );
      }
    };
  }, []);

  const showBookingMessage = useCallback(
    (message: BookingMessage, duration = 5000) => {
      if (bookingMessageTimerRef.current !== null) {
        window.clearTimeout(
          bookingMessageTimerRef.current
        );
      }

      setBookingMessage(message);

      bookingMessageTimerRef.current =
        window.setTimeout(() => {
          setBookingMessage(null);
          bookingMessageTimerRef.current = null;
        }, duration);
    },
    []
  );

  const clearBookingMessage = useCallback(() => {
    if (bookingMessageTimerRef.current !== null) {
      window.clearTimeout(
        bookingMessageTimerRef.current
      );
      bookingMessageTimerRef.current = null;
    }

    setBookingMessage(null);
  }, []);

  const handleHostelClick = useCallback(
    (hostel: Hostel) => {
      setSelectedHostelId(hostel.id);
      setMetroRoute(null);
      clearBookingMessage();
    },
    [clearBookingMessage]
  );

  const handleCloseCard = useCallback(() => {
    setSelectedHostelId(null);
    setMetroRoute(null);
    clearBookingMessage();
  }, [clearBookingMessage]);

  const handleBook = useCallback(
    async (hostelId: number) => {
      clearBookingMessage();

      try {
        const result = await bookHostel({ hostelId });

        if (!result.success) {
          throw new Error(
            result.message ?? "Бронь не создана"
          );
        }

        setBookedHostelIds((current) =>
          current.includes(hostelId)
            ? current
            : [...current, hostelId]
        );

        showBookingMessage({
          type: "success",
          text: "Место успешно забронировано!",
        });

        /*
         * /api/places — источник истины для количества мест,
         * manager_info и booking. После успешной брони сразу
         * перечитываем пункты, поэтому вкладка "Контакты и бронь"
         * обновляется без перезагрузки страницы.
         */
        try {
          await reloadHostels();
        } catch (reloadError) {
          console.error(
            "Не удалось обновить список после бронирования:",
            reloadError
          );
        }
      } catch (error) {
        console.error("Ошибка бронирования:", error);

        showBookingMessage({
          type: "error",
          text:
            error instanceof Error
              ? error.message
              : "Не удалось забронировать место. Попробуйте ещё раз.",
        });
      }
    },
    [clearBookingMessage, reloadHostels, showBookingMessage]
  );

  return (
    <div className="app">
      <MoscowMap
        hostels={hostels}
        userLocation={mapLocation}
        onHostelClick={handleHostelClick}
        route={metroRoute}
        selectedHostel={selectedHostel}
      />

      {hostelsLoading && hostels.length === 0 && (
        <div className="map-status">
          Загружаем пункты...
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
            role="alertdialog"
            aria-live="assertive"
            className="booking-notice-overlay"
            onClick={clearBookingMessage}
          >
            <div
              className={`booking-notice booking-notice--${bookingMessage.type}`}
              onClick={(event) => event.stopPropagation()}
            >
              <div className="booking-notice__icon">
                {bookingMessage.type === "success"
                  ? "✓"
                  : "!"}
              </div>

              <div className="booking-notice__body">
                <div className="booking-notice__title">
                  {bookingMessage.type === "success"
                    ? "Бронирование успешно"
                    : "Не удалось забронировать"}
                </div>

                <div className="booking-notice__text">
                  {bookingMessage.text}
                </div>
              </div>

              <button
                type="button"
                className="booking-notice__close"
                onClick={clearBookingMessage}
                aria-label="Закрыть уведомление"
              >
                ×
              </button>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}

export default App;
