import type { Hostel } from "../../types";

interface HostelCardProps {
  hostel: Hostel;
  onClose: () => void;
  onBook: () => void;
  onContacts: () => void;
}

export default function HostelCard({
  hostel,
  onClose,
  onBook,
  onContacts,
}: HostelCardProps) {
  return (
    <div className="hostel-card">
      <button
        className="hostel-card__close"
        onClick={onClose}
        aria-label="Закрыть"
      >
        ×
      </button>

      <h2>{hostel.name}</h2>

      <p className="hostel-card__address">
        📍 {hostel.address}
      </p>

      <div className="hostel-card__info">
        <div>
          🛏 Свободных мест:
          <strong>{hostel.bedsAvailable}</strong>
          {" "}из {hostel.bedsTotal}
        </div>
      </div>

      <p className="hostel-card__description">
        {hostel.description}
      </p>

      <div className="hostel-card__buttons">
        <button
          className="hostel-card__book"
          onClick={onBook}
        >
          Забронировать
        </button>

        <button
          className="hostel-card__contacts"
          onClick={onContacts}
        >
          Контакты
        </button>
      </div>
    </div>
  );
}