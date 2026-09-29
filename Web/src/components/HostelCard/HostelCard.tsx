import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import type { Hostel, UserLocation } from "../../types";
import type {
  BookingInfo,
  ManagerInfo,
} from "../../api/hostels";

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

type HostelWithServerData = Hostel & {
  managerInfo?: ManagerInfo | null;
  booking?: BookingInfo | null;
  homestayType?: number;
};

interface DragState {
  active: boolean;
  startY: number;
  startOffset: number;
  currentOffset: number;
  maxOffset: number;
}

function getDistanceKm(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  const R = 6371;

  const lat1Rad = (lat1 * Math.PI) / 180;
  const lat2Rad = (lat2 * Math.PI) / 180;

  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1Rad) *
      Math.cos(lat2Rad) *
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

  // 00:00 — 00:00 обычно означает круглосуточно.
  if (openMinutes === closeMinutes) {
    return true;
  }

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

function isMobileViewport(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(max-width: 600px)").matches
  );
}

function formatServerDate(value: string): string {
  if (!value) {
    return "Не указано";
  }

  // Сервер присылает ISO без гарантированной timezone.
  // Не сдвигаем время браузерной таймзоной, а показываем
  // ровно то локальное время, которое пришло с backend.
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/
  );

  if (!match) {
    return value;
  }

  const [, year, month, day, hour, minute] = match;
  return `${day}.${month}.${year} ${hour}:${minute}`;
}

function getBookingStatus(booking: BookingInfo): string {
  if (booking.is_approved === 1) {
    return "Подтверждено";
  }

  if (booking.is_approved === 0) {
    return "Ожидает подтверждения";
  }

  return `Статус: ${booking.is_approved}`;
}

export default function HostelCard({
  hostel,
  userLocation,
  onClose,
  onShowRoute,
  booked,
  onBook,
}: HostelCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const dragRef = useRef<DragState>({
    active: false,
    startY: 0,
    startOffset: 0,
    currentOffset: 0,
    maxOffset: 0,
  });

  const [showContacts, setShowContacts] =
    useState(false);

  const [showRoute, setShowRoute] =
    useState(false);

  const [booking, setBooking] =
    useState(false);

  const [sheetOffset, setSheetOffset] =
    useState(0);

  const [sheetDragging, setSheetDragging] =
    useState(false);

  const [, setCurrentTime] =
    useState(Date.now());

  const hostelData = hostel as HostelWithServerData;
  const managerInfo = hostelData.managerInfo ?? null;
  const serverBooking = hostelData.booking ?? null;

  const isBooked = booked || serverBooking !== null;

  const getCollapsedOffset = (): number => {
    if (!isMobileViewport()) {
      return 0;
    }

    const height =
      cardRef.current?.getBoundingClientRect().height ?? 0;

    // Оставляем сверху примерно 124px панели:
    // drag-handle, название и начало адреса.
    return Math.max(0, height - 124);
  };

  const setSheetPosition = (collapsed: boolean) => {
    if (!isMobileViewport()) {
      dragRef.current.currentOffset = 0;
      setSheetOffset(0);
      return;
    }

    const nextOffset = collapsed
      ? getCollapsedOffset()
      : 0;

    dragRef.current.currentOffset = nextOffset;
    setSheetOffset(nextOffset);
  };

  useEffect(() => {
    setShowContacts(false);
    setShowRoute(false);
    setBooking(false);
    setSheetOffset(0);
    dragRef.current.currentOffset = 0;
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

  useEffect(() => {
    const handleResize = () => {
      if (!isMobileViewport()) {
        dragRef.current.currentOffset = 0;
        setSheetOffset(0);
        return;
      }

      const maxOffset = getCollapsedOffset();

      setSheetOffset((current) => {
        const next = Math.min(current, maxOffset);
        dragRef.current.currentOffset = next;
        return next;
      });
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const currentlyOpen =
    hostel.isWorking &&
    isCurrentlyOpen(
      hostel.openTime,
      hostel.closeTime
    );

  const distance = getDistanceKm(
    userLocation.lat,
    userLocation.lng,
    hostel.lat,
    hostel.lng
  );

  const nearestMetro = getNearestMetro(
    hostel.lat,
    hostel.lng
  );

  const userMetro = getNearestMetro(
    userLocation.lat,
    userLocation.lng
  );

  const userToMetroDistance = getDistanceKm(
    userLocation.lat,
    userLocation.lng,
    userMetro.lat,
    userMetro.lng
  );

  const hostelToMetroDistance = getDistanceKm(
    hostel.lat,
    hostel.lng,
    nearestMetro.lat,
    nearestMetro.lng
  );

  // Не пытаемся строить маршрут Московского метро для тестовых
  // пунктов в Петербурге, Омске, Краснодаре и других городах.
  const metroAvailable =
    userToMetroDistance <= 20 &&
    hostelToMetroDistance <= 20;

  const metroRoute = metroAvailable
    ? findMetroRoute(userMetro, nearestMetro)
    : null;

  const userMetroWalkingTime = metroAvailable
    ? getWalkingTime(
        userLocation.lat,
        userLocation.lng,
        userMetro
      )
    : 0;

  const walkingTime = metroAvailable
    ? getWalkingTime(
        hostel.lat,
        hostel.lng,
        nearestMetro
      )
    : 0;

  const handleBook = async () => {
    if (booking || isBooked) {
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
      return;
    }

    setShowRoute(true);
    onShowRoute(metroRoute);

    // На телефоне сразу опускаем карточку,
    // чтобы построенный на карте маршрут был виден.
    if (isMobileViewport()) {
      if (cardRef.current) {
        cardRef.current.scrollTop = 0;
      }

      window.requestAnimationFrame(() => {
        setSheetPosition(true);
      });
    }
  };

  const handleContacts = () => {
    setShowContacts((current) => !current);
    setSheetPosition(false);

    if (cardRef.current) {
      cardRef.current.scrollTop = 0;
    }
  };

  const handleSheetPointerDown = (
    event: ReactPointerEvent<HTMLDivElement>
  ) => {
    if (!isMobileViewport()) {
      return;
    }

    event.preventDefault();

    const maxOffset = getCollapsedOffset();

    dragRef.current = {
      active: true,
      startY: event.clientY,
      startOffset: sheetOffset,
      currentOffset: sheetOffset,
      maxOffset,
    };

    setSheetDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handleSheetPointerMove = (
    event: ReactPointerEvent<HTMLDivElement>
  ) => {
    const state = dragRef.current;

    if (!state.active) {
      return;
    }

    event.preventDefault();

    const delta = event.clientY - state.startY;
    const next = Math.min(
      state.maxOffset,
      Math.max(0, state.startOffset + delta)
    );

    state.currentOffset = next;
    setSheetOffset(next);
  };

  const finishSheetDrag = (
    event: ReactPointerEvent<HTMLDivElement>
  ) => {
    const state = dragRef.current;

    if (!state.active) {
      return;
    }

    state.active = false;
    setSheetDragging(false);

    const delta = event.clientY - state.startY;

    // Явный свайп вниз/вверх имеет приоритет.
    // При маленьком движении выбираем ближайшее положение.
    const collapse =
      delta > 42 ||
      (delta >= -42 &&
        state.currentOffset > state.maxOffset / 2);

    const nextOffset = collapse
      ? state.maxOffset
      : 0;

    state.currentOffset = nextOffset;
    setSheetOffset(nextOffset);

    try {
      event.currentTarget.releasePointerCapture(
        event.pointerId
      );
    } catch {
      // Pointer capture мог уже освободиться браузером.
    }
  };

  return (
    <div
      ref={cardRef}
      className={`hostel-card ${
        sheetDragging ? "hostel-card--dragging" : ""
      }`}
      style={{
        transform: `translateX(-50%) translateY(${sheetOffset}px)`,
      }}
    >
      <div
        className="hostel-card__sheet-handle-area"
        onPointerDown={handleSheetPointerDown}
        onPointerMove={handleSheetPointerMove}
        onPointerUp={finishSheetDrag}
        onPointerCancel={finishSheetDrag}
        aria-label="Потяните вниз, чтобы свернуть карточку, или вверх, чтобы открыть"
      >
        <span className="hostel-card__sheet-handle" />
      </div>

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
                ? `${Math.round(distance * 1000)} м`
                : `${distance.toFixed(1)} км`}
            </strong>
          </div>

          <div className="hostel-card__info">
            🛏 Свободных мест:{" "}
            <strong>{hostel.bedsAvailable}</strong>{" "}
            из {hostel.bedsTotal}
          </div>

          {serverBooking && (
            <div className="hostel-card__booking-banner">
              <span>🎫</span>
              <div>
                <strong>У вас есть бронирование</strong>
                <small>
                  {getBookingStatus(serverBooking)} ·{" "}
                  {formatServerDate(
                    serverBooking.date_time
                  )}
                </small>
              </div>
            </div>
          )}

          <div className="hostel-card__metro">
            <div className="hostel-card__metro-title">
              🚇 Как добраться на метро
            </div>

            {!metroAvailable ? (
              <div className="hostel-card__metro-unavailable">
                <span>ℹ️</span>
                <div>
                  <strong>Маршрут метро недоступен</strong>
                  <small>
                    Этот пункт или ваше текущее местоположение находятся
                    далеко от Московского метро.
                  </small>
                </div>
              </div>
            ) : (
              <>
              <div className="hostel-card__metro-route">
                <div className="hostel-card__metro-point">
                  <span>📍</span>

                  <div>
                    <small>
                      Ближайшая станция к вам
                    </small>

                    <strong>{userMetro.name}</strong>

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

                    <strong>{nearestMetro.name}</strong>

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
                    ? "✕ Скрыть маршрут с карты"
                    : "🚇 Показать маршрут на карте"}
                </button>
              )}

              {showRoute && metroRoute && (
                <div className="hostel-card__route-status">
                  <span>✓</span>
                  <div>
                    <strong>
                      Маршрут отображается на карте
                    </strong>
                    <small>
                      {metroRoute.durationMinutes > 0 &&
                        `≈ ${metroRoute.durationMinutes} мин`}
                      {metroRoute.durationMinutes > 0 &&
                        metroRoute.transferCount > 0 &&
                        " · "}
                      {metroRoute.transferCount > 0 &&
                        `${metroRoute.transferCount} ${
                          metroRoute.transferCount === 1
                            ? "пересадка"
                            : metroRoute.transferCount < 5
                              ? "пересадки"
                              : "пересадок"
                        }`}
                    </small>
                  </div>
                </div>
              )}
              </>
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
                isBooked
                  ? "hostel-card__book--success"
                  : ""
              }`}
              onClick={handleBook}
              disabled={
                booking ||
                isBooked ||
                hostel.bedsAvailable <= 0
              }
            >
              {booking
                ? "Бронируем..."
                : isBooked
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
              ☎ Контакты и бронь
            </button>
          </div>
        </div>
      ) : (
        <div className="hostel-card__content hostel-card__content--contacts">
          <div className="hostel-card__contacts-icon">
            ☎
          </div>

          <h2>Контакты и бронирование</h2>

          <section className="hostel-card__details-section">
            <h3>Менеджер пункта</h3>

            {managerInfo ? (
              <div className="hostel-card__details-card">
                <div className="hostel-card__contact-item">
                  <span>👤</span>
                  <div>
                    <small>Имя</small>
                    <strong>
                      {managerInfo.username ||
                        "Не указано"}
                    </strong>
                  </div>
                </div>

                <div className="hostel-card__contact-item">
                  <span>📞</span>
                  <div>
                    <small>Телефон</small>
                    {managerInfo.phone_number ? (
                      <a
                        href={`tel:${managerInfo.phone_number}`}
                      >
                        {managerInfo.phone_number}
                      </a>
                    ) : (
                      <strong>Не указан</strong>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="hostel-card__empty-state">
                <span>ℹ️</span>
                <div>
                  <strong>
                    Менеджер пока не назначен
                  </strong>
                  <small>
                    Контактные данные менеджера пока не указаны.
                  </small>
                </div>
              </div>
            )}
          </section>

          <section className="hostel-card__details-section">
            <h3>Ваше бронирование</h3>

            {serverBooking ? (
              <div className="hostel-card__details-card">
                <div className="hostel-card__contact-item">
                  <span>🎫</span>
                  <div>
                    <small>Статус</small>
                    <strong>
                      {getBookingStatus(serverBooking)}
                    </strong>
                  </div>
                </div>

                <div className="hostel-card__contact-item">
                  <span>🕐</span>
                  <div>
                    <small>Дата бронирования</small>
                    <strong>
                      {formatServerDate(
                        serverBooking.date_time
                      )}
                    </strong>
                  </div>
                </div>

                <div className="hostel-card__contact-item">
                  <span>№</span>
                  <div>
                    <small>Номер бронирования</small>
                    <strong>{serverBooking.id}</strong>
                  </div>
                </div>
              </div>
            ) : (
              <div className="hostel-card__empty-state">
                <span>ℹ️</span>
                <div>
                  <strong>
                    Бронирования этого пункта нет
                  </strong>
                  <small>
                    Вы ещё не бронировали место в этом пункте.
                  </small>
                </div>
              </div>
            )}
          </section>

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
