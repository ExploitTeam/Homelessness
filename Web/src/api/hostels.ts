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

  // ИМЕННО названия из твоей БД
  longtitude: number | null;
  latitude: number | null;
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
    const text = await response.text();

    throw new Error(
      `Ошибка бронирования: ${response.status} ${text}`
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