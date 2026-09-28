const API_URL = "https://homelessness.bot.nu";

let accessToken: string | null = null;

function getMaxInitData(): string {
  return window.WebApp?.initData ?? "";
}

async function authorize(): Promise<string> {
  if (accessToken) {
    return accessToken;
  }

  const initData = getMaxInitData();

  if (!initData) {
    throw new Error(
      "Приложение запущено не внутри MAX: отсутствует initData"
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
    throw new Error(
      `Ошибка авторизации: ${response.status}`
    );
  }

  const data: {
    access_token: string;
  } = await response.json();

  accessToken = data.access_token;

  return accessToken;
}

export interface ManagerInfo {
  id: number;
  username: string;
  user_type: number;
  phone_number: string;
  id_homestay: number;
  last_booking: string;
}

export interface BookingInfo {
  id: number;
  user_id: number;
  homestay_id: number;
  date_time: string;
  is_approved: number;
}

export interface BackendPlace {
  id: number;
  address: string;
  available_beds: number;
  all_beds: number;
  open_time: string;
  close_time: string;
  is_working: number;
  additional_info: string | null;
  homestay_type: number;

  // именно названия из БД
  longtitude: number | null;
  latitude: number | null;

  manager_info:
    | ManagerInfo
    | Record<string, never>;

  booking:
    | BookingInfo
    | Record<string, never>;
}

interface PlacesResponse {
  user_id: number;
  places: BackendPlace[];
}

export async function getHostels(): Promise<BackendPlace[]> {
  const token = await authorize();

  const response = await fetch(`${API_URL}/api/places`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(
      `Ошибка загрузки ночлежек: ${response.status}`
    );
  }

  const data: PlacesResponse = await response.json();

  console.log("PLACES FROM SERVER:", data);

  return data.places;
}

export interface BookHostelParams {
  hostelId: number;
}

export interface BookHostelResponse {
  success: boolean;
  message?: string;
}

export async function bookHostel(
  params: BookHostelParams
): Promise<BookHostelResponse> {
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

  if (!response.ok) {
    let serverMessage = "";

    try {
      const data = await response.json();

      if (typeof data?.message === "string") {
        serverMessage = data.message;
      }
    } catch {
      // Сервер мог вернуть не JSON
    }

    if (response.status === 404) {
      throw new Error(
        serverMessage ||
          "Пункт или пользователь не найден"
      );
    }

    if (response.status === 400) {
      throw new Error(
        serverMessage ||
          "Нет доступных мест в данном пункте"
      );
    }

    if (response.status === 429) {
      throw new Error(
        serverMessage ||
          "Повторное бронирование возможно только через 5 минут"
      );
    }

    throw new Error(
      serverMessage ||
        `Ошибка бронирования: ${response.status}`
    );
  }

  const data: {
    message?: string;
  } = await response.json();

  return {
    success: true,
    message: data.message,
  };
}