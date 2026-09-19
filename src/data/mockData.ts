import type { Hostel, UserLocation } from "../types";

export const mockHostels: Hostel[] = [
  {
    id: 1,
    name: "Ночлежка на Тверской",
    address: "Москва, ул. Тверская, 10",
    lat: 55.764,
    lng: 37.605,
    bedsAvailable: 8,
    bedsTotal: 30,
    description:
      "Ночлежка для геев в центре Москвы. Есть места для временного проживания",
    phone: "+7 (666) 123-45-67",
    email: "info@example.ru",
  },

  {
    id: 2,
    name: "Ночлежка на Арбате",
    address: "Москва, ул. Арбат, 20",
    lat: 55.752,
    lng: 37.592,
    bedsAvailable: 4,
    bedsTotal: 20,
    description:
      "Небольшая ночлежка рядом с Арбатом(только для геев)",
    phone: "+7 (999) 234-56-78",
    email: "arbat@example.ru",
  },
];

export const mockUserLocation: UserLocation = {
  lat: 55.7558,
  lng: 37.6173,
};