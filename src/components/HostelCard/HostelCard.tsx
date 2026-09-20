import { useState } from "react";

import type { Hostel } from "../../types";

interface HostelCardProps {
  hostel: Hostel;
  onClose: () => void;
}

export default function HostelCard({
  hostel,
  onClose,
}: HostelCardProps) {
  const [showContacts, setShowContacts] =
    useState(false);

  const [booking, setBooking] =
    useState(false);

  const [booked, setBooked] =
    useState(false);

  const handleBook = () => {
    if (booking || booked) {
      return;
    }

    setBooking(true);

    // Пока имитация запроса на сервер
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