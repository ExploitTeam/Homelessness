import type {
  Hostel,
  UserLocation,
} from "../types";

import { mockHostels } from "../data/mockData";

const API_URL = import.meta.env.VITE_API_URL;

export async function getHostels(
  location: UserLocation
): Promise<Hostel[]> {
  if (!API_URL) {
    console.log(
      "Backend пока не подключён. Используем тестовые данные."
    );

    return mockHostels;
  }

  const response = await fetch(
    `${API_URL}/api/hostels?lat=${location.lat}&lng=${location.lng}`
  );

  if (!response.ok) {
    throw new Error(
      "Не удалось получить список ночлежек"
    );
  }

  return response.json();
}

/*
 * БРОНИРОВАНИЕ
 */
export interface BookingRequest {
  hostelId: number;
  userLocation: UserLocation;
}

export interface BookingResponse {
  success: boolean;
  message?: string;
  bookingId?: string;
}

export async function bookHostel(
  data: BookingRequest
): Promise<BookingResponse> {
  /*
   * Если backend ещё не подключён,
   * просто имитируем успешный ответ.
   */
  if (!API_URL) {
    console.log(
      "Backend пока не подключён."
    );

    console.log(
      "Условный запрос на бронь:",
      data
    );

    await new Promise((resolve) =>
      setTimeout(resolve, 1000)
    );

    return {
      success: true,
      message:
        "Бронь успешно создана (тестовый режим)",
      bookingId:
        `test-${data.hostelId}-${Date.now()}`,
    };
  }

  /*
   * Реальный запрос на backend.
   */
  const response = await fetch(
    `${API_URL}/api/bookings`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        hostelId: data.hostelId,

        userLocation: {
          lat: data.userLocation.lat,
          lng: data.userLocation.lng,
        },
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      "Не удалось забронировать место"
    );
  }

  return response.json();
}