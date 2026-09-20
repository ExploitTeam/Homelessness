import type { Hostel } from "../types";
import {
  metroStations,
  type MetroStation,
} from "../data/metroData";

//Получаем дистанцию
function getDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  const R = 6371;

  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;

  return (
    R *
    2 *
    Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  );
}

export function getNearestMetro(
  hostel: Hostel
): MetroStation {
  let nearest = metroStations[0];
  let nearestDistance = Infinity;

  for (const station of metroStations) {
    const distance = getDistance(
      hostel.lat,
      hostel.lng,
      station.lat,
      station.lng
    );

    if (distance < nearestDistance) {
      nearest = station;
      nearestDistance = distance;
    }
  }

  return nearest;
}

export function getWalkingTime(
  hostel: Hostel,
  station: MetroStation
): number {
  const distance = getDistance(
    hostel.lat,
    hostel.lng,
    station.lat,
    station.lng
  );

  //Примерно 5 км/ч скорость пешком? наверное да
  return Math.max(1, Math.round((distance / 5) * 60));
}