import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent, type TouchEvent as ReactTouchEvent } from "react";

import type { UserLocation } from "../../types";
import type { HostelWithApiData } from "../../hooks/useHostels";
import { findMetroRoute, getNearestMetro, getWalkingTime, type MetroRoute } from "../../utils/metro";

interface HostelCardProps {
  hostel: HostelWithApiData;
  userLocation: UserLocation;
  onClose: () => void;
  onShowRoute: (route: MetroRoute | null) => void;
  booked: boolean;
  onBook: (hostelId: number) => void | Promise<void>;
}

type Drag = {
  startY: number;
  startOffset: number;
  currentOffset: number;
  maxOffset: number;
  mode: "mouse" | "touch";
};

function distanceKm(a: UserLocation, b: UserLocation): number {
  const toRad = (n: number) => (n * Math.PI) / 180;
  const deltaLat = toRad(b.lat - a.lat);
  const deltaLng = toRad(b.lng - a.lng);
  const x = Math.sin(deltaLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(deltaLng / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

function formatDistance(value: number): string {
  return value < 1 ? `${Math.round(value * 1000)} м` : `${value.toFixed(1).replace(".", ",")} км`;
}

function formatDate(value: string): string {
  const date = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(value);
  return date ? `${date[3]}.${date[2]}.${date[1]} в ${date[4]}:${date[5]}` : value || "Не указана";
}

function bookingStatus(value: number): string {
  return value === 1 ? "Подтверждено" : "Ожидает подтверждения";
}

function getSchedule(open: string, close: string): string | null {
  if (!open || !close) return null;
  if (open.slice(0, 5) === close.slice(0, 5)) return "Круглосуточно";
  return `${open.slice(0, 5)}–${close.slice(0, 5)}`;
}

export default function HostelCard({ hostel, userLocation, onClose, onShowRoute, booked, onBook }: HostelCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const contactsRef = useRef<HTMLElement>(null);
  const dragRef = useRef<Drag | null>(null);
  const suppressClickRef = useRef(false);
  const [collapsed, setCollapsed] = useState(false);
  const [dragOffset, setDragOffset] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showRoute, setShowRoute] = useState(false);

  const isBooked = booked || hostel.booking !== null;
  const canBook = !isBooked && hostel.bedsAvailable > 0;
  const schedule = getSchedule(hostel.openTime || "", hostel.closeTime || "");
  const distance = distanceKm(userLocation, { lat: hostel.lat, lng: hostel.lng });

  const pointMetro = getNearestMetro(hostel.lat, hostel.lng);
  const userMetro = getNearestMetro(userLocation.lat, userLocation.lng);
  const metroAvailable =
    distanceKm(userLocation, { lat: userMetro.lat, lng: userMetro.lng }) <= 20 &&
    distanceKm({ lat: hostel.lat, lng: hostel.lng }, { lat: pointMetro.lat, lng: pointMetro.lng }) <= 20;
  const metroRoute = metroAvailable ? findMetroRoute(userMetro, pointMetro) : null;

  useEffect(() => {
    setCollapsed(false);
    setDragOffset(null);
    setShowRoute(false);
    onShowRoute(null);
    scrollRef.current?.scrollTo({ top: 0 });
  }, [hostel.id, onShowRoute]);

  function openContacts() {
    setCollapsed(false);
    const scroll = scrollRef.current;
    const target = contactsRef.current;
    if (!scroll || !target) return;
    const top = target.getBoundingClientRect().top - scroll.getBoundingClientRect().top + scroll.scrollTop - 14;
    scroll.scrollTo({ top, behavior: "smooth" });
  }

  async function submitBooking() {
    if (!canBook || saving) return;
    setSaving(true);
    try {
      await onBook(hostel.id);
    } finally {
      setSaving(false);
    }
  }

  function toggleRoute() {
    if (!metroRoute) return;
    const next = !showRoute;
    setShowRoute(next);
    onShowRoute(next ? metroRoute : null);
    if (next) setCollapsed(true);
  }

  // Двигается только специальная верхняя ручка; прокрутка текста, контактов
  // и нажатия на нижние кнопки не конфликтуют с перемещением карточки.
  function beginDrag(clientY: number, mode: Drag["mode"]) {
    const height = cardRef.current?.getBoundingClientRect().height ?? 0;
    const maxOffset = Math.max(0, height - 108);
    const startOffset = collapsed ? maxOffset : 0;
    dragRef.current = { startY: clientY, startOffset, currentOffset: startOffset, maxOffset, mode };
    setDragOffset(startOffset);
    setDragging(true);
  }

  useEffect(() => {
    function move(clientY: number) {
      const drag = dragRef.current;
      if (!drag) return;
      drag.currentOffset = Math.min(drag.maxOffset, Math.max(0, drag.startOffset + clientY - drag.startY));
      setDragOffset(drag.currentOffset);
    }
    function finish(clientY: number) {
      const drag = dragRef.current;
      if (!drag) return;
      dragRef.current = null;
      setDragging(false);
      setDragOffset(null);
      const delta = clientY - drag.startY;
      setCollapsed(Math.abs(delta) < 10 ? !collapsed : delta > 45 || (delta >= -45 && drag.currentOffset > drag.maxOffset / 2));
      suppressClickRef.current = true;
      window.setTimeout(() => { suppressClickRef.current = false; }, 350);
    }
    const onMouseMove = (event: MouseEvent) => {
      if (dragRef.current?.mode !== "mouse") return;
      event.preventDefault();
      move(event.clientY);
    };
    const onMouseUp = (event: MouseEvent) => {
      if (dragRef.current?.mode === "mouse") finish(event.clientY);
    };
    const onTouchMove = (event: TouchEvent) => {
      if (dragRef.current?.mode !== "touch") return;
      const touch = event.touches[0];
      if (touch) { event.preventDefault(); move(touch.clientY); }
    };
    const onTouchEnd = (event: TouchEvent) => {
      if (dragRef.current?.mode === "touch") finish(event.changedTouches[0]?.clientY ?? dragRef.current.startY);
    };
    window.addEventListener("mousemove", onMouseMove, { passive: false });
    window.addEventListener("mouseup", onMouseUp);
    window.addEventListener("touchmove", onTouchMove, { passive: false });
    window.addEventListener("touchend", onTouchEnd);
    window.addEventListener("touchcancel", onTouchEnd);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
      window.removeEventListener("touchcancel", onTouchEnd);
    };
  }, [collapsed]);

  function dragMouseDown(event: ReactMouseEvent<HTMLButtonElement>) {
    if (event.button !== 0) return;
    event.preventDefault();
    beginDrag(event.clientY, "mouse");
  }
  function dragTouchStart(event: ReactTouchEvent<HTMLButtonElement>) {
    if (event.touches[0]) beginDrag(event.touches[0].clientY, "touch");
  }

  return (
    <article
      ref={cardRef}
      className={`place-sheet${collapsed ? " place-sheet--collapsed" : ""}${dragging ? " place-sheet--dragging" : ""}`}
      style={dragOffset === null ? undefined : { transform: `translate3d(-50%, ${dragOffset}px, 0)` }}
      aria-label={`Информация о пункте: ${hostel.address}`}
    >
      <button
        type="button"
        className="place-sheet__handle-control"
        aria-label={collapsed ? "Развернуть карточку пункта" : "Свернуть карточку пункта"}
        aria-expanded={!collapsed}
        onMouseDown={dragMouseDown}
        onTouchStart={dragTouchStart}
        onClick={() => {
          if (!suppressClickRef.current) setCollapsed((current) => !current);
        }}
      >
        <span className="place-sheet__handle" aria-hidden="true" />
      </button>

      <div className="place-sheet__topline">
        <div className="place-sheet__heading">
          <span className="place-sheet__eyebrow">ПУНКТ ПОМОЩИ</span>
          <h2>{hostel.categoryLabel}</h2>
          <p>📍 {hostel.address}</p>
        </div>
        <button type="button" className="place-sheet__close" onClick={onClose} aria-label="Закрыть карточку">×</button>
      </div>

      <div ref={scrollRef} className="place-sheet__scroll">
        <div className="place-sheet__overview">
          <div className={`place-sheet__status${hostel.isWorking ? " place-sheet__status--active" : ""}`}>
            <span aria-hidden="true">●</span>
            {hostel.isWorking ? "Пункт работает" : "Пункт временно не работает"}
          </div>
          <div className="place-sheet__facts">
            <div><span className="place-sheet__fact-icon">↗</span><small>Расстояние по прямой</small><strong>{formatDistance(distance)}</strong></div>
            <div><span className="place-sheet__fact-icon">🛏️</span><small>Свободных мест</small><strong>{hostel.bedsTotal > 0 ? `${hostel.bedsAvailable} из ${hostel.bedsTotal}` : "Не указано"}</strong></div>
            <div><span className="place-sheet__fact-icon">🕒</span><small>Время работы</small><strong>{schedule ?? "Уточняйте"}</strong></div>
          </div>
        </div>

        <section className="place-sheet__section place-sheet__fund" aria-labelledby="place-fund-title">
          <div className="place-sheet__section-title"><span aria-hidden="true">🤝</span><h3 id="place-fund-title">Организация</h3></div>
          <div className="place-sheet__fund-content">
            <span className="place-sheet__meta-label">Благотворительный фонд</span>
            <strong className="place-sheet__fund-name">{hostel.fund?.name || "Фонд не указан"}</strong>
            {hostel.fund?.description ? (
              <p className="place-sheet__description">{hostel.fund.description}</p>
            ) : (
              <p className="place-sheet__muted">Описание фонда пока не добавлено.</p>
            )}
          </div>
        </section>

        <section className="place-sheet__section" aria-labelledby="place-about-title">
          <div className="place-sheet__section-title"><span aria-hidden="true">📋</span><h3 id="place-about-title">О пункте</h3></div>
          <p className={hostel.description ? "place-sheet__description" : "place-sheet__muted"}>
            {hostel.description || "Дополнительная информация о пункте пока не указана."}
          </p>
        </section>

        {hostel.booking && (
          <section className="place-sheet__section place-sheet__booking" aria-labelledby="place-booking-title">
            <div className="place-sheet__section-title"><span aria-hidden="true">🎟️</span><h3 id="place-booking-title">Моя бронь</h3></div>
            <p className="place-sheet__booking-status">{bookingStatus(hostel.booking.is_approved)}</p>
            <p>Заявка №{hostel.booking.id} · {formatDate(hostel.booking.date_time)}</p>
          </section>
        )}

        <section ref={contactsRef} className="place-sheet__section place-sheet__contacts" aria-labelledby="place-contacts-title">
          <div className="place-sheet__section-title"><span aria-hidden="true">☎️</span><h3 id="place-contacts-title">Контакты пункта</h3></div>
          {hostel.managers.length === 0 ? (
            <p className="place-sheet__muted">Контактные лица пока не указаны.</p>
          ) : (
            <div className="place-sheet__managers">
              {hostel.managers.map((manager, index) => (
                <div className="place-sheet__manager" key={`${index}-${manager.name}`}>
                  <div className="place-sheet__manager-avatar" aria-hidden="true">👤</div>
                  <div className="place-sheet__manager-details">
                    <strong>{manager.name || "Сотрудник пункта"}</strong>
                    <span>Контактное лицо</span>
                    {manager.phone ? (
                      <a href={`tel:${manager.phone.replace(/[^\d+]/g, "")}`}>📞 {manager.phone}</a>
                    ) : (
                      <small>Номер телефона не указан</small>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="place-sheet__section" aria-labelledby="place-route-title">
          <div className="place-sheet__section-title"><span aria-hidden="true">🗺️</span><h3 id="place-route-title">Как добраться</h3></div>
          <details className="place-sheet__route-details">
            <summary>Маршрут на метро <span aria-hidden="true">⌄</span></summary>
            {metroAvailable && metroRoute ? (
              <div className="place-sheet__route-content">
                <p><strong>От:</strong> {userMetro.name} <small>({getWalkingTime(userLocation.lat, userLocation.lng, userMetro)} мин пешком до станции)</small></p>
                <p><strong>До:</strong> {pointMetro.name} <small>({getWalkingTime(hostel.lat, hostel.lng, pointMetro)} мин пешком до пункта)</small></p>
                <button type="button" className="place-sheet__route-button" onClick={toggleRoute}>
                  {showRoute ? "Скрыть маршрут с карты" : "Показать на карте"}
                </button>
              </div>
            ) : <p className="place-sheet__muted">Маршрут Московского метро для этого пункта недоступен.</p>}
          </details>
        </section>
      </div>

      <footer className="place-sheet__actions" aria-label="Действия с пунктом">
        <button type="button" className="place-sheet__contact-button" onClick={openContacts}>☎️ Контакты</button>
        <button
          type="button"
          className={`place-sheet__book-button${isBooked ? " place-sheet__book-button--booked" : ""}`}
          disabled={saving || !canBook}
          onClick={submitBooking}
        >
          {saving ? "Отправляем…" : isBooked ? "✓ Заявка подана" : hostel.bedsAvailable <= 0 ? "Нет мест" : "Забронировать"}
        </button>
      </footer>
    </article>
  );
}
