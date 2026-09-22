import type { UserLocation } from "../types";

const API_URL = "https://homelessness.bot.nu";

interface BackendPlace {
  id: number;
  address: string;
  all_beds: number;
  available_beds: number;
  open_time: string;
  close_time: string;
  is_working: number;
  additional_info: string | null;
  homestay_type?: number | null;
}

interface PlacesResponse {
  user_id: number;
  places: BackendPlace[];
}

interface AuthResponse {
  access_token: string;
  token_type: string;
}

interface BookResponse {
  status?: string;
  message?: string;
  detail?: string;
}

let accessToken: string | null = null;

function getMaxInitData(): string {
  return window.WebApp?.initData ?? "";
}

function getDemoHostels(): HostelApiItem[] {
  return [
    {
      id: 1,
      address: "Ленина 5",
      all_beds: 20,
      available_beds: 20,
      open_time: "16:30",
      close_time: "06:10",
      is_working: true,
      additional_info: "Новый пункт обогрева. Всю зиму.",
      homestay_type: null,
    },
    {
      id: 2,
      address: "Москва, demo-пункт №2",
      all_beds: 15,
      available_beds: 8,
      open_time: "20:00",
      close_time: "08:00",
      is_working: true,
      additional_info: "Пункт обогрева. С октября по апрель.",
      homestay_type: null,
    },
    {
      id: 3,
      address: "Пр. Девятого Января, 8",
      all_beds: 10,
      available_beds: 4,
      open_time: "20:00",
      close_time: "08:00",
      is_working: true,
      additional_info: "Ночной приют. Круглый год.",
      homestay_type: null,
    },
  ];
}

async function authorize(): Promise<string> {
  if (accessToken) {
    return accessToken;
  }

  const initData = getMaxInitData();

  if (!initData) {
    throw new Error(
      "MAX initData отсутствует. Открой приложение внутри MAX."
    );
  }

  const response = await fetch(`${API_URL}/api/auth`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      initData,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Ошибка авторизации: ${text}`);
  }

  const data: AuthResponse = await response.json();

  accessToken = data.access_token;

  return accessToken;
}

export interface HostelApiItem {
  id: number;
  address: string;
  all_beds: number;
  available_beds: number;
  open_time: string;
  close_time: string;
  is_working: boolean;
  additional_info: string;
  homestay_type: number | null;
}

export async function getHostels(
  _userLocation?: UserLocation
): Promise<HostelApiItem[]> {
  const initData = getMaxInitData();

  if (!initData) {
    console.log("MAX initData отсутствует — используем демо-данные.");
    return getDemoHostels();
  }

  const token = await authorize();

  const response = await fetch(`${API_URL}/api/places`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      accessToken = null;
    }

    const text = await response.text();
    throw new Error(`Не удалось загрузить ночлежки: ${text}`);
  }

  const data: PlacesResponse = await response.json();

  return data.places.map((place) => ({
    id: place.id,
    address: place.address,
    all_beds: place.all_beds,
    available_beds: place.available_beds,
    open_time: place.open_time,
    close_time: place.close_time,
    is_working: Boolean(place.is_working),
    additional_info: place.additional_info ?? "",
    homestay_type: place.homestay_type ?? null,
  }));
}

export async function bookHostel(params: {
  hostelId: number;
  userLocation?: UserLocation;
}): Promise<{
  success: boolean;
  message?: string;
}> {
  const initData = getMaxInitData();

  // Локальный режим: имитируем успешную бронь.
  if (!initData) {
    console.log(
      `Демо-бронирование ночлежки №${params.hostelId}`
    );

    return {
      success: true,
      message: "Место успешно забронировано (демо-режим)",
    };
  }

  try {
    const token = await authorize();

    const response = await fetch(`${API_URL}/api/book`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        id_homestay: params.hostelId,
      }),
    });

    const data: BookResponse = await response.json();

    if (!response.ok) {
      return {
        success: false,
        message:
          data.detail ?? "Не удалось забронировать место",
      };
    }

    return {
      success: data.status === "success",
      message: data.message,
    };
  } catch (error) {
    console.error("Ошибка бронирования:", error);

    return {
      success: false,
      message:
        error instanceof Error
          ? error.message
          : "Не удалось забронировать место",
    };
  }
}