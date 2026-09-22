import {
  metroLines,
  metroStations,
  type MetroStation,
} from "../data/metroData";

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
    Math.atan2(
      Math.sqrt(a),
      Math.sqrt(1 - a)
    )
  );
}

export function getNearestMetro(
  lat: number,
  lng: number
): MetroStation {
  let nearest = metroStations[0];
  let nearestDistance = Infinity;

  for (const station of metroStations) {
    const d = getDistance(
      lat,
      lng,
      station.lat,
      station.lng
    );

    if (d < nearestDistance) {
      nearestDistance = d;
      nearest = station;
    }
  }

  return nearest;
}

export function getWalkingTime(
  lat: number,
  lng: number,
  station: MetroStation
): number {
  const distance = getDistance(
    lat,
    lng,
    station.lat,
    station.lng
  );

  return Math.max(
    1,
    Math.round((distance / 5) * 60)
  );
}

interface GraphEdge {
  to: string;
  line: string;
  weight: number;
}

export interface MetroRoute {
  stations: MetroStation[];
  lines: string[];
}

function buildGraph(): Map<string, GraphEdge[]> {
  const graph = new Map<string, GraphEdge[]>();

  for (const station of metroStations) {
    graph.set(station.id, []);
  }

  for (const line of metroLines) {
    for (
      let i = 0;
      i < line.stations.length - 1;
      i++
    ) {
      const currentName = line.stations[i][0];
      const nextName = line.stations[i + 1][0];

      const current = metroStations.find(
        (station) => station.name === currentName
      );

      const next = metroStations.find(
        (station) => station.name === nextName
      );

      if (!current || !next) continue;

      graph.get(current.id)?.push({
        to: next.id,
        line: line.name,
        weight: 1,
      });

      graph.get(next.id)?.push({
        to: current.id,
        line: line.name,
        weight: 1,
      });
    }
  }

  /*
   * Пересадки.
   *
   * Если одна станция принадлежит нескольким линиям,
   * она уже объединена одним id.
   *
   * Поэтому переход с одной линии на другую
   * происходит внутри одной станции.
   */

  return graph;
}

export function findMetroRoute(
  start: MetroStation,
  end: MetroStation
): MetroRoute | null {
  if (start.id === end.id) {
    return {
      stations: [start],
      lines: start.lines,
    };
  }

  const graph = buildGraph();

  const distances = new Map<string, number>();
  const previous = new Map<
    string,
    string | null
  >();

  const queue: string[] = [];

  for (const station of metroStations) {
    distances.set(station.id, Infinity);
    previous.set(station.id, null);
  }

  distances.set(start.id, 0);
  queue.push(start.id);

  while (queue.length > 0) {
    queue.sort(
      (a, b) =>
        (distances.get(a) ?? Infinity) -
        (distances.get(b) ?? Infinity)
    );

    const current = queue.shift();

    if (!current) break;

    if (current === end.id) {
      break;
    }

    const edges = graph.get(current) ?? [];

    for (const edge of edges) {
      const newDistance =
        (distances.get(current) ?? Infinity) +
        edge.weight;

      if (
        newDistance <
        (distances.get(edge.to) ?? Infinity)
      ) {
        distances.set(edge.to, newDistance);
        previous.set(edge.to, current);

        if (!queue.includes(edge.to)) {
          queue.push(edge.to);
        }
      }
    }
  }

  if (
    (distances.get(end.id) ?? Infinity) ===
    Infinity
  ) {
    return null;
  }

  const routeIds: string[] = [];

  let current: string | null = end.id;

  while (current !== null) {
    routeIds.unshift(current);
    current = previous.get(current) ?? null;
  }

  const stations = routeIds
    .map((id) =>
      metroStations.find(
        (station) => station.id === id
      )
    )
    .filter(
      (station): station is MetroStation =>
        station !== undefined
    );

  const lines: string[] = [];

  for (const station of stations) {
    for (const line of station.lines) {
      if (!lines.includes(line)) {
        lines.push(line);
      }
    }
  }

  return {
    stations,
    lines,
  };
}