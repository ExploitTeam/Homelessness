import {
  useEffect,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type TouchEvent as ReactTouchEvent,
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
  input: "mouse" | "touch" | null;
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
    input: null,
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
    const height = cardRef.current?.offsetHeight ?? 0;

    // На телефоне оставляем видимыми ручку + заголовок/часть адреса.
    // На desktop/fullscreen оставляем компактную полоску с ручкой,
    // чтобы карта почти полностью была доступна после построения маршрута.
    const peekHeight = isMobileViewport() ? 124 : 72;

    return Math.max(0, height - peekHeight);
  };

  const setSheetPosition = (collapsed: boolean) => {
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

    // После построения маршрута опускаем карточку на любом размере экрана.
    // На телефоне остаётся видимой верхняя часть карточки, на desktop/fullscreen
    // — компактная полоска с ручкой. Карточку можно вытянуть обратно
    // вверх пальцем или мышкой.
    if (cardRef.current) {
      cardRef.current.scrollTop = 0;
    }

    // Два кадра дают React/WebView MAX время применить новый DOM,
    // после чего высота карточки измеряется корректно и она сворачивается.
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        setSheetPosition(true);
      });
    });
  };

  const handleContacts = () => {
    setShowContacts((current) => !current);
    setSheetPosition(false);

    if (cardRef.current) {
      cardRef.current.scrollTop = 0;
    }
  };

  const beginSheetDrag = (
    clientY: number,
    input: "mouse" | "touch"
  ) => {
    const maxOffset = getCollapsedOffset();

    dragRef.current = {
      active: true,
      input,
      startY: clientY,
      startOffset: sheetOffset,
      currentOffset: sheetOffset,
      maxOffset,
    };

    setSheetDragging(true);
  };

  const updateSheetDrag = (clientY: number) => {
    const state = dragRef.current;

    if (!state.active) {
      return;
    }

    const delta = clientY - state.startY;
    const next = Math.min(
      state.maxOffset,
      Math.max(0, state.startOffset + delta)
    );

    state.currentOffset = next;
    setSheetOffset(next);
  };

  const finishSheetDragAt = (clientY: number) => {
    const state = dragRef.current;

    if (!state.active) {
      return;
    }

    const delta = clientY - state.startY;
    const movement = Math.abs(delta);

    state.active = false;
    state.input = null;
    setSheetDragging(false);

    let nextOffset: number;

    if (movement <= 8) {
      /*
       * В MAX WebView простой клик надёжнее drag-жеста.
       * Поэтому короткое нажатие по верхней ручке переключает
       * состояние карточки в обе стороны:
       * раскрыта -> свернуть, свернута -> раскрыть.
       */
      const wasCollapsed =
        state.startOffset > state.maxOffset / 2;

      nextOffset = wasCollapsed
        ? 0
        : state.maxOffset;
    } else {
      const collapse =
        delta > 42 ||
        (delta >= -42 &&
          state.currentOffset > state.maxOffset / 2);

      nextOffset = collapse
        ? state.maxOffset
        : 0;
    }

    state.currentOffset = nextOffset;
    setSheetOffset(nextOffset);

    if (nextOffset === 0 && cardRef.current) {
      cardRef.current.scrollTop = 0;
    }
  };

  const handleSheetMouseDown = (
    event: ReactMouseEvent<HTMLDivElement>
  ) => {
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    beginSheetDrag(event.clientY, "mouse");
  };

  const handleSheetTouchStart = (
    event: ReactTouchEvent<HTMLDivElement>
  ) => {
    const touch = event.touches[0];

    if (!touch) {
      return;
    }

    event.preventDefault();
    beginSheetDrag(touch.clientY, "touch");
  };

  const handleSheetTouchMove = (
    event: ReactTouchEvent<HTMLDivElement>
  ) => {
    const state = dragRef.current;

    if (!state.active || state.input !== "touch") {
      return;
    }

    const touch = event.touches[0];

    if (!touch) {
      return;
    }

    event.preventDefault();
    updateSheetDrag(touch.clientY);
  };

  const handleSheetTouchEnd = (
    event: ReactTouchEvent<HTMLDivElement>
  ) => {
    const state = dragRef.current;

    if (!state.active || state.input !== "touch") {
      return;
    }

    const touch = event.changedTouches[0];
    finishSheetDragAt(touch?.clientY ?? state.startY);
  };

  const toggleSheet = () => {
    const maxOffset = getCollapsedOffset();
    const collapsed = sheetOffset > maxOffset / 2;
    setSheetPosition(!collapsed);

    if (collapsed && cardRef.current) {
      cardRef.current.scrollTop = 0;
    }
  };

  /*
   * В desktop/MAX не используем setPointerCapture.
   * Движение мыши отслеживаем на window, поэтому карточка продолжает
   * следовать за курсором даже если он вышел за пределы ручки.
   */
  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      const state = dragRef.current;

      if (!state.active || state.input !== "mouse") {
        return;
      }

      event.preventDefault();
      updateSheetDrag(event.clientY);
    };

    const handleMouseUp = (event: MouseEvent) => {
      const state = dragRef.current;

      if (!state.active || state.input !== "mouse") {
        return;
      }

      finishSheetDragAt(event.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove, {
      passive: false,
    });
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  });

  return (
    <div
      ref={cardRef}
      className={`hostel-card ${
        sheetDragging ? "hostel-card--dragging" : ""
      } ${
        sheetOffset > 8 ? "hostel-card--collapsed" : ""
      }`}
      style={{
        transform: `translateX(-50%) translateY(${sheetOffset}px)`,
      }}
    >
      {sheetOffset > 8 && (
        <div
          className="hostel-card__collapsed-hitbox"
          role="button"
          tabIndex={0}
          aria-label="Открыть карточку"
          onMouseDown={handleSheetMouseDown}
          onTouchStart={handleSheetTouchStart}
          onTouchMove={handleSheetTouchMove}
          onTouchEnd={handleSheetTouchEnd}
          onTouchCancel={handleSheetTouchEnd}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              setSheetPosition(false);
            }
          }}
        />
      )}

      <div
        className="hostel-card__sheet-handle-area"
        role="button"
        tabIndex={0}
        onMouseDown={handleSheetMouseDown}
        onTouchStart={handleSheetTouchStart}
        onTouchMove={handleSheetTouchMove}
        onTouchEnd={handleSheetTouchEnd}
        onTouchCancel={handleSheetTouchEnd}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            toggleSheet();
          }
        }}
        aria-label={
          sheetOffset > 8
            ? "Развернуть карточку"
            : "Свернуть карточку"
        }
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
