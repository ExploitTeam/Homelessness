import type { Hostel, UserLocation } from "../types";

export const mockHostels: Hostel[] = [
  {
    id: 1,
    name: "Ночлежка на Ленина",
    address: "Ленина 5",
    lat: 55.7558,
    lng: 37.6176,
    bedsAvailable: 20,
    bedsTotal: 20,
    description:
      "Новый пункт обогрева. Всю зиму.",
    phone: "8 800 000-00-01",
    email: "info@example.ru",
    openTime: "16:30",
    closeTime: "06:10",
    isWorking: true,
  },
  {
    id: 2,
    name: "Пункт обогрева Арбат",
    address: "Москва, Арбат",
    lat: 55.7887,
    lng: 37.6767,
    bedsAvailable: 8,
    bedsTotal: 15,
    description:
      "Пункт обогрева. С октября по апрель.",
    phone: "8 800 000-00-02",
    email: "arbat@example.ru",
    openTime: "20:00",
    closeTime: "08:00",
    isWorking: true,
  },
];

export const mockUserLocation: UserLocation = {
  lat: 55.751244,
  lng: 37.618423,
};