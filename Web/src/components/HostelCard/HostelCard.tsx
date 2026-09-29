import { useEffect, useState } from "react";

import type { Hostel, UserLocation } from "../../types";

import {
  findMetroRoute,
  getNearestMetro,
  getWalkingTime,
  type MetroRoute,
} from "../../utils/metro";

interface HostelCardProps {
  hostel: Hostel;
  userLocation: UserLocation;
  onClose: () => void;
  onShowRoute: (route: MetroRoute | null) => void;
  booked: boolean;
  onBook: (hostelId: number) => void | Promise<void>;
}

function getDistance(
  userLocation: UserLocation,
  hostel: Hostel
): number {
  const R = 6371;

  const lat1 =
    (userLocation.lat * Math.PI) / 180;

  const lat2 =
    (hostel.lat * Math.PI) / 180;

  const dLat =
    ((hostel.lat - userLocation.lat) * Math.PI) /
    180;

  const dLng =
    ((hostel.lng - userLocation.lng) * Math.PI) /
    180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) *
      Math.cos(lat2) *
      Math.sin(dLng / 2) ** 2;

  const c =
    2 *
    Math.atan2(
      Math.sqrt(a),
      Math.sqrt(1 - a)
    );

  return R * c;
}

function isCurrentlyOpen(
  openTime: string,
  closeTime: string
): boolean {
  if (!openTime || !closeTime) {
    return false;
  }

  const now = new Date();

  const moscowTime = new Intl.DateTimeFormat(
    "ru-RU",
    {
      timeZone: "Europe/Moscow",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }
  ).format(now);

  const [currentHour, currentMinute] =
    moscowTime.split(":").map(Number);

  if (
    Number.isNaN(currentHour) ||
    Number.isNaN(currentMinute)
  ) {
    return false;
  }

  const currentMinutes =
    currentHour * 60 + currentMinute;

  const [openHour, openMinute] =
    openTime.split(":").map(Number);

  const [closeHour, closeMinute] =
    closeTime.split(":").map(Number);

  if (
    Number.isNaN(openHour) ||
    Number.isNaN(openMinute) ||
    Number.isNaN(closeHour) ||
    Number.isNaN(closeMinute)
  ) {
    return false;
  }

  const openMinutes =
    openHour * 60 + openMinute;

  const closeMinutes =
    closeHour * 60 + closeMinute;

  if (closeMinutes < openMinutes) {
    return (
      currentMinutes >= openMinutes ||
      currentMinutes < closeMinutes
    );
  }

  return (
    currentMinutes >= openMinutes &&
    currentMinutes < closeMinutes
  );
}

export default function HostelCard({
  hostel,
  userLocation,
  onClose,
  onShowRoute,
  booked,
  onBook,
}: HostelCardProps) {
  const [showContacts, setShowContacts] =
    useState(false);

  const [showRoute, setShowRoute] =
    useState(false);

  const [booking, setBooking] =
    useState(false);

  const [, setCurrentTime] =
    useState(Date.now());

  useEffect(() => {
    setShowContacts(false);
    setShowRoute(false);
    setBooking(false);
    onShowRoute(null);
  }, [hostel.id, onShowRoute]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setCurrentTime(Date.now());
    }, 30000);

    return () => {
      window.clearInterval(interval);
    };
  }, []);

  const currentlyOpen =
    hostel.isWorking &&
    isCurrentlyOpen(
      hostel.openTime,
      hostel.closeTime
    );

  const distance = getDistance(
    userLocation,
    hostel
  );

  const nearestMetro = getNearestMetro(
    hostel.lat,
    hostel.lng
  );

  const userMetro = getNearestMetro(
    userLocation.lat,
    userLocation.lng
  );

  const metroRoute = findMetroRoute(
    userMetro,
    nearestMetro
  );

  const userMetroWalkingTime =
    getWalkingTime(
      userLocation.lat,
      userLocation.lng,
      userMetro
    );

  const walkingTime = getWalkingTime(
    hostel.lat,
    hostel.lng,
    nearestMetro
  );

  const handleBook = async () => {
    if (booking || booked) {
      return;
    }

    setBooking(true);

    try {
      await onBook(hostel.id);
    } finally {
      setBooking(false);
    }
  };

  const handleRoute = () => {
    if (!metroRoute) {
      return;
    }

    if (showRoute) {
      setShowRoute(false);
      onShowRoute(null);
    } else {
      setShowRoute(true);
      onShowRoute(metroRoute);
    }
  };

  const handleContacts = () => {
    setShowContacts((current) => !current);
  };

  return (
    <div className="hostel-card">
      <button
        type="button"
        className="hostel-card__close"
        onClick={onClose}
        aria-label="Закрыть"
      >
        ×
      </button>

      {!showContacts ? (
        <div className="hostel-card__content hostel-card__content--main">
          <h2>{hostel.name}</h2>

          <p className="hostel-card__address">
            📍 {hostel.address}
          </p>

          <div
            className={`hostel-card__working ${
              currentlyOpen
                ? "hostel-card__working--open"
                : "hostel-card__working--closed"
            }`}
          >
            <span className="hostel-card__working-icon">
              {currentlyOpen ? "🟢" : "🔴"}
            </span>

            <div className="hostel-card__working-text">
              <strong>
                {currentlyOpen
                  ? "Сейчас работает"
                  : "Сейчас закрыто"}
              </strong>

              {hostel.openTime &&
                hostel.closeTime && (
                  <small>
                    🕐 {hostel.openTime} —{" "}
                    {hostel.closeTime}
                  </small>
                )}
            </div>
          </div>

          <div className="hostel-card__distance">
            <span>🚶</span>

            <span>Расстояние:</span>

            <strong>
              {distance < 1
                ? `${Math.round(
                    distance * 1000
                  )} м`
                : `${distance.toFixed(1)} км`}
            </strong>
          </div>

          <div className="hostel-card__info">
            🛏 Свободных мест:{" "}
            <strong>
              {hostel.bedsAvailable}
            </strong>{" "}
            из {hostel.bedsTotal}
          </div>

          <div className="hostel-card__metro">
            <div className="hostel-card__metro-title">
              🚇 Как добраться на метро
            </div>

            <div className="hostel-card__metro-route">
              <div className="hostel-card__metro-point">
                <span>📍</span>

                <div>
                  <small>
                    Ближайшая станция к вам
                  </small>

                  <strong>
                    {userMetro.name}
                  </strong>

                  <span>
                    {userMetro.lines.join(" / ")}
                  </span>
                </div>
              </div>

              <div className="hostel-card__metro-arrow">
                ↓
              </div>

              <div className="hostel-card__metro-point">
                <span>🏠</span>

                <div>
                  <small>
                    Ближайшая к ночлежке
                  </small>

                  <strong>
                    {nearestMetro.name}
                  </strong>

                  <span>
                    {nearestMetro.lines.join(" / ")}
                  </span>
                </div>
              </div>
            </div>

            <div className="hostel-card__metro-walk">
              🚶 До станции от вас примерно{" "}
              {userMetroWalkingTime} мин
            </div>

            <div className="hostel-card__metro-walk">
              🚶 От станции до ночлежки примерно{" "}
              {walkingTime} мин
            </div>

            {metroRoute && (
              <button
                type="button"
                className="hostel-card__route-button"
                onClick={handleRoute}
              >
                {showRoute
                  ? "✕ Скрыть маршрут"
                  : "🚇 Показать маршрут"}
              </button>
            )}

            {showRoute && metroRoute && (
              <div className="hostel-card__route">
                <div className="hostel-card__route-title">
                  🚇 Маршрут метро
                </div>

                {metroRoute.stations.map(
                  (station, index) => {
                    const first =
                      index === 0;

                    const last =
                      index ===
                      metroRoute.stations.length - 1;

                    const transfer =
                      station.lines.length > 1;

                    return (
                      <div
                        className="hostel-card__route-station"
                        key={`${station.id}-${index}`}
                      >
                        <span>
                          {first
                            ? "📍"
                            : last
                              ? "🏠"
                              : transfer
                                ? "🔄"
                                : "🚇"}
                        </span>

                        <div>
                          <strong>
                            {station.name}
                          </strong>

                          <small>
                            {station.lines.join(
                              " / "
                            )}
                          </small>
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            )}
          </div>

          <p className="hostel-card__description">
            {hostel.description ||
              "Дополнительная информация отсутствует."}
          </p>

          <div className="hostel-card__buttons">
            <button
              type="button"
              className={`hostel-card__book ${
                booked
                  ? "hostel-card__book--success"
                  : ""
              }`}
              onClick={handleBook}
              disabled={
                booking ||
                booked ||
                hostel.bedsAvailable <= 0
              }
            >
              {booking
                ? "Бронируем..."
                : booked
                  ? "Забронировано ✓"
                  : hostel.bedsAvailable <= 0
                    ? "Мест нет"
                    : "Забронировать"}
            </button>

            <button
              type="button"
              className="hostel-card__contacts"
              onClick={handleContacts}
            >
              ☎ Контакты
            </button>
          </div>
        </div>
      ) : (
        <div className="hostel-card__content hostel-card__content--contacts">
          <div className="hostel-card__contacts-icon">
            ☎
          </div>

          <h2>
            Контактная информация
          </h2>

          {hostel.phone || hostel.email ? (
            <>
              {hostel.phone && (
                <div className="hostel-card__contact-item">
                  <span>📞</span>
                  <span>{hostel.phone}</span>
                </div>
              )}

              {hostel.email && (
                <div className="hostel-card__contact-item">
                  <span>✉️</span>
                  <span>{hostel.email}</span>
                </div>
              )}
            </>
          ) : (
            <div className="hostel-card__contact-item">
              <span>ℹ️</span>

              <span>
                Контактные данные пока не указаны.
              </span>
            </div>
          )}

          <button
            type="button"
            className="hostel-card__back"
            onClick={handleContacts}
          >
            ← Назад
          </button>
        </div>
      )}
    </div>
  );
}