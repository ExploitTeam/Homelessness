import { useState } from "react";

import type { Hostel, UserLocation } from "../../types";

interface HostelCardProps {
  hostel: Hostel;
  userLocation: UserLocation;
  onClose: () => void;
}

function getDistance(
  userLocation: UserLocation,
  hostel: Hostel
): number {
  const R = 6371;

  const lat1 = (userLocation.lat * Math.PI) / 180;
  const lat2 = (hostel.lat * Math.PI) / 180;

  const dLat =
    ((hostel.lat - userLocation.lat) * Math.PI) / 180;

  const dLng =
    ((hostel.lng - userLocation.lng) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) *
      Math.cos(lat2) *
      Math.sin(dLng / 2) ** 2;

  const c =
    2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

export default function HostelCard({
  hostel,
  userLocation,
  onClose,
}: HostelCardProps) {
  const [showContacts, setShowContacts] =
    useState(false);

  const [booking, setBooking] =
    useState(false);

  const [booked, setBooked] =
    useState(false);

  const distance = getDistance(
    userLocation,
    hostel
  );

  const handleBook = () => {
    if (booking || booked) {
      return;
    }

    setBooking(true);

    setTimeout(() => {
      setBooking(false);
      setBooked(true);
    }, 1000);
  };

  const handleContacts = () => {
    setShowContacts((current) => !current);
  };

  return (
    <div className="hostel-card">
      <button
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

          <p className="hostel-card__distance">
            🚶 Расстояние:{" "}
            <strong>
              {distance < 1
                ? `${Math.round(distance * 1000)} м`
                : `${distance.toFixed(1)} км`}
            </strong>
          </p>

          <div className="hostel-card__info">
            🛏 Свободных мест:
            <strong>{hostel.bedsAvailable}</strong>
            {" "}из {hostel.bedsTotal}
          </div>

          <p className="hostel-card__description">
            {hostel.description}
          </p>

          <div className="hostel-card__buttons">
            <button
              className={`hostel-card__book ${
                booked
                  ? "hostel-card__book--success"
                  : ""
              }`}
              onClick={handleBook}
              disabled={booking || booked}
            >
              {booking
                ? "Бронируем..."
                : booked
                  ? "Забронировано ✓"
                  : "Забронировать"}
            </button>

            <button
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

          <h2>Контактная информация</h2>

          <div className="hostel-card__contact-item">
            <span>📞</span>
            <span>{hostel.phone}</span>
          </div>

          <div className="hostel-card__contact-item">
            <span>✉️</span>
            <span>{hostel.email}</span>
          </div>

          <button
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