import type { Hostel, UserLocation } from "../types";
import { mockHostels } from "../data/mockData";

const API_URL = import.meta.env.VITE_API_URL;

export async function getHostels(
  location: UserLocation
): Promise<Hostel[]> {
  // сорян пока backend не написан
  // здесь будет настоящий fetch

  if (!API_URL) {
    console.log(
      "Backend пока не подключён. Используем тестовые данные"
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