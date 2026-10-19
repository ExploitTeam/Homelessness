// В одном контейнере фронт и API находятся на одном origin. При отдельном
// хостинге веб-сайта задайте <meta name="max-api-base-url" content="https://...">.
// Это предотвращает незаметное обращение новой сборки к старому API-серверу.
const configuredApi = document.querySelector<HTMLMetaElement>('meta[name="max-api-base-url"]')?.content.trim();
const API_URL = (configuredApi || window.location.origin).replace(/\/+$/, "");

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

export interface PublicManager {
  name: string;
  phone: string | null;
}

export interface FundInfo {
  name: string;
  description: string;
}

// Поддержка старого API при обновлении фронта и сервера по отдельности.
export interface ManagerInfo {
  username: string;
  phone_number: string | null;
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
  longtitude: number | null;
  latitude: number | null;
  fund?: FundInfo | null;
  category_label?: string;
  managers?: PublicManager[];
  manager_info: ManagerInfo | Record<string, never>;
  booking: BookingInfo | Record<string, never>;
}

interface PlacesResponse {
  user_id: number;
  places: BackendPlace[];
}

export async function getHostels(): Promise<
  BackendPlace[]
> {
  const token = await authorize();

  const response = await fetch(
    `${API_URL}/api/places`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `Ошибка загрузки пунктов: ${response.status}`
    );
  }

  const data: PlacesResponse =
    await response.json();

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

  const response = await fetch(
    `${API_URL}/api/book`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },

      body: JSON.stringify({
        id_homestay: params.hostelId,
      }),
    }
  );

  /*
   * Обработка ошибок бронирования
   */
  if (!response.ok) {
    let serverMessage = "";

    /*
     * Ответ сервера читаем для console.error,
     * но напрямую пользователю его не показываем.
     */
    try {
      const responseText =
        await response.text();

      if (responseText) {
        try {
          const data =
            JSON.parse(responseText);

          if (typeof data === "string") {
            serverMessage = data;
          } else if (
            typeof data?.message === "string"
          ) {
            serverMessage = data.message;
          } else if (
            typeof data?.detail === "string"
          ) {
            serverMessage = data.detail;
          } else if (
            typeof data?.error === "string"
          ) {
            serverMessage = data.error;
          }
        } catch {
          serverMessage = responseText;
        }
      }
    } catch {
      // Не удалось прочитать ответ сервера
    }

    console.error(
      "Ошибка бронирования:",
      {
        status: response.status,
        serverMessage,
      }
    );

    /*
     * 404
     *
     * Пункт или пользователь не найден
     */
    if (response.status === 404) {
      throw new Error(
        "Не удалось найти выбранный пункт или ваш профиль. Обновите приложение и попробуйте снова."
      );
    }

    /*
     * 400
     *
     * Нет доступных мест
     */
    if (response.status === 400) {
      throw new Error(
        "К сожалению, в этом пункте сейчас нет свободных мест."
      );
    }

    /*
     * 429
     *
     * Повторный запрос в течение 5 секунд
     */
    if (response.status === 429) {
      throw new Error(
        "Вы слишком быстро отправили повторный запрос. Подождите 5 секунд и попробуйте снова."
      );
    }

    /*
     * 409
     *
     * Эта ночлежка уже забронирована
     * данным пользователем
     */
    if (response.status === 409) {
      throw new Error(
        "Вы уже забронировали место в этом пункте."
      );
    }

    /*
     * Любая другая ошибка.
     *
     * Технический ответ backend пользователю
     * не показываем.
     */
    throw new Error(
      "Не удалось забронировать место. Попробуйте ещё раз."
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