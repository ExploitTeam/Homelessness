import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  AttributionControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import type {
  Hostel,
  UserLocation,
} from "../../types";

import type { MetroRoute } from "../../utils/metro";

import {
  getMetroLinePaths,
  metroLines,
  metroStations,
} from "../../data/metroData";

setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

interface MoscowMapProps {
  hostels: Hostel[];
  userLocation: UserLocation;
  onHostelClick: (hostel: Hostel) => void;
  route: MetroRoute | null;
  selectedHostel?: Hostel | null;
}

interface MetroStationView {
  name: string;
  lat: number;
  lng: number;
  colors: string[];
}

const METRO_LAYER_IDS = [
  "metro-network-line",
  "metro-network-double-a",
  "metro-network-double-b",
] as const;

const ROUTE_SOURCE_ID = "selected-metro-route";
const ROUTE_HALO_LAYER_ID = "selected-metro-route-halo";
const ROUTE_LAYER_ID = "selected-metro-route-line";
const TRANSFER_SOURCE_ID = "selected-metro-transfers";
const TRANSFER_HALO_LAYER_ID = "selected-metro-transfer-halo";
const TRANSFER_LAYER_ID = "selected-metro-transfer-line";

function removeMarkers(markers: Marker[]) {
  markers.forEach((marker) => marker.remove());
  markers.length = 0;
}

function isMobileViewport() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(max-width: 600px)").matches
  );
}

export default function MoscowMap({
  hostels,
  userLocation,
  onHostelClick,
  route,
  selectedHostel = null,
}: MoscowMapProps) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);

  const hostelMarkers = useRef<Marker[]>([]);
  const routeMarkers = useRef<Marker[]>([]);
  const metroMarkers = useRef<Marker[]>([]);

  const [metroVisible, setMetroVisible] = useState(false);
  const metroVisibleRef = useRef(false);

  const applyMetroVisibility = useCallback(
    (visible: boolean) => {
      metroVisibleRef.current = visible;
      setMetroVisible(visible);

      const mapInstance = map.current;

      if (!mapInstance) {
        return;
      }

      for (const layerId of METRO_LAYER_IDS) {
        if (mapInstance.getLayer(layerId)) {
          mapInstance.setLayoutProperty(
            layerId,
            "visibility",
            visible ? "visible" : "none"
          );
        }
      }

      metroMarkers.current.forEach((marker) => {
        marker.getElement().style.display = visible
          ? "flex"
          : "none";
      });
    },
    []
  );

  /*
   * =====================================
   * СОЗДАНИЕ КАРТЫ + СЕТЬ МЕТРО
   * =====================================
   */
  useEffect(() => {
    if (!mapContainer.current || map.current) {
      return;
    }

    const newMap = new MapLibreMap({
      container: mapContainer.current,
      center: [37.6173, 55.7558],
      zoom: 11,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: [
              "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            ],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      },
    });

    map.current = newMap;

    newMap.addControl(
      new NavigationControl({ showCompass: false }),
      "top-right"
    );

    newMap.addControl(
      new AttributionControl({ compact: true }),
      "bottom-right"
    );

    const handleLoad = () => {
      if (newMap.getSource("metro-network")) {
        return;
      }

      const features = metroLines.flatMap((line) =>
        getMetroLinePaths(line)
          .filter((path) => path.length >= 2)
          .map((path) => ({
            type: "Feature" as const,
            properties: {
              color: line.color,
              name: line.name,
              lineId: line.id,
              render: line.render ?? "solid",
            },
            geometry: {
              type: "LineString" as const,
              coordinates: path.map(
                ([, lat, lng]) => [lng, lat]
              ),
            },
          }))
      );

      newMap.addSource("metro-network", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features,
        },
      });

      // Обычные линии метро.
      newMap.addLayer({
        id: "metro-network-line",
        type: "line",
        source: "metro-network",
        filter: ["!=", ["get", "render"], "double"],
        layout: {
          visibility: "none",
          "line-cap": "round",
          "line-join": "round",
        },
        paint: {
          "line-color": ["get", "color"],
          "line-width": 4.5,
          "line-opacity": 0.9,
        },
      });

      // МЦК отображаем двумя параллельными красными линиями.
      for (const [id, offset] of [
        ["metro-network-double-a", -2.2],
        ["metro-network-double-b", 2.2],
      ] as const) {
        newMap.addLayer({
          id,
          type: "line",
          source: "metro-network",
          filter: ["==", ["get", "render"], "double"],
          layout: {
            visibility: "none",
            "line-cap": "round",
            "line-join": "round",
          },
          paint: {
            "line-color": ["get", "color"],
            "line-width": 2.4,
            "line-offset": offset,
            "line-opacity": 0.92,
          },
        });
      }

      const stationMap = new globalThis.Map<
        string,
        MetroStationView
      >();

      for (const station of metroStations) {
        if (
          !Number.isFinite(station.lat) ||
          !Number.isFinite(station.lng)
        ) {
          continue;
        }

        const key = `${station.name}_${station.lat.toFixed(
          5
        )}_${station.lng.toFixed(5)}`;

        const existing = stationMap.get(key);

        if (existing) {
          if (!existing.colors.includes(station.color)) {
            existing.colors.push(station.color);
          }
          continue;
        }

        stationMap.set(key, {
          name: station.name,
          lat: station.lat,
          lng: station.lng,
          colors: [station.color],
        });
      }

      stationMap.forEach((station) => {
        const element = document.createElement("div");
        element.className = "metro-station-marker";
        element.title = station.name;

        // Станции — только визуальный слой. Они не должны
        // перехватывать нажатия по пунктам размещения.
        element.style.pointerEvents = "none";
        element.style.display = metroVisibleRef.current
          ? "flex"
          : "none";

        if (station.colors.length === 1) {
          element.style.background = station.colors[0];
        } else {
          const sectors = station.colors.map(
            (color, index) => {
              const start =
                (index / station.colors.length) * 100;
              const end =
                ((index + 1) / station.colors.length) * 100;
              return `${color} ${start}% ${end}%`;
            }
          );

          element.style.background = `conic-gradient(${sectors.join(
            ", "
          )})`;
        }

        const marker = new Marker({
          element,
          anchor: "center",
        })
          .setLngLat([station.lng, station.lat])
          .addTo(newMap);

        metroMarkers.current.push(marker);
      });

      applyMetroVisibility(metroVisibleRef.current);
    };

    newMap.on("load", handleLoad);

    return () => {
      newMap.off("load", handleLoad);

      removeMarkers(metroMarkers.current);
      removeMarkers(hostelMarkers.current);
      removeMarkers(routeMarkers.current);

      newMap.remove();
      map.current = null;
    };
  }, [applyMetroVisibility]);

  /*
   * =====================================
   * ПОЛЬЗОВАТЕЛЬ + ПУНКТЫ
   * =====================================
   */
  useEffect(() => {
    const mapInstance = map.current;

    if (!mapInstance) {
      return;
    }

    removeMarkers(hostelMarkers.current);

    const userElement = document.createElement("div");
    userElement.className = "user-marker";
    userElement.title = "Ваше местоположение";
    userElement.style.pointerEvents = "none";

    const userMarker = new Marker({
      element: userElement,
      anchor: "center",
    })
      .setLngLat([userLocation.lng, userLocation.lat])
      .addTo(mapInstance);

    hostelMarkers.current.push(userMarker);

    for (const hostel of hostels) {
      if (
        !Number.isFinite(hostel.lat) ||
        !Number.isFinite(hostel.lng)
      ) {
        continue;
      }

      const element = document.createElement("button");
      element.type = "button";
      element.className = "hostel-marker";
      element.dataset.hostelId = String(hostel.id);
      element.title = hostel.name;
      element.setAttribute(
        "aria-label",
        `Открыть пункт: ${hostel.name}`
      );

      element.textContent = "⌂";
      element.style.background = hostel.isWorking
        ? "#ef4444"
        : "#6b7280";
      element.style.pointerEvents = "auto";
      element.style.touchAction = "manipulation";

      if (selectedHostel?.id === hostel.id) {
        element.classList.add("hostel-marker--selected");
      }

      const stopMapGesture = (event: Event) => {
        event.stopPropagation();
      };

      const handleClick = (event: MouseEvent) => {
        event.preventDefault();
        event.stopPropagation();
        onHostelClick(hostel);
      };

      element.addEventListener("pointerdown", stopMapGesture);
      element.addEventListener("click", handleClick);

      const marker = new Marker({
        element,
        anchor: "center",
      })
        .setLngLat([hostel.lng, hostel.lat])
        .addTo(mapInstance);

      hostelMarkers.current.push(marker);
    }

    return () => {
      removeMarkers(hostelMarkers.current);
    };
  }, [
    hostels,
    onHostelClick,
    selectedHostel?.id,
    userLocation.lat,
    userLocation.lng,
  ]);

  /*
   * =====================================
   * МАРКЕРЫ ВЫБРАННОГО МАРШРУТА
   * =====================================
   */
  useEffect(() => {
    const mapInstance = map.current;

    if (!mapInstance) {
      return;
    }

    removeMarkers(routeMarkers.current);

    if (!route || route.stations.length === 0) {
      return;
    }

    const importantStations = new globalThis.Map<
      string,
      { station: MetroRoute["stations"][number]; icon: string }
    >();

    const first = route.stations[0];
    const last = route.stations[route.stations.length - 1];

    for (const transfer of route.transfers) {
      importantStations.set(transfer.from.id, {
        station: transfer.from,
        icon: "↻",
      });
      importantStations.set(transfer.to.id, {
        station: transfer.to,
        icon: "↻",
      });
    }

    // A/B должны оставаться видимыми даже если старт/финиш
    // одновременно являются пересадочными платформами.
    importantStations.set(first.id, {
      station: first,
      icon: "A",
    });

    importantStations.set(last.id, {
      station: last,
      icon: first.id === last.id ? "A" : "B",
    });

    importantStations.forEach(({ station, icon }) => {
      const element = document.createElement("div");
      element.className = "metro-route-marker";
      element.textContent = icon;
      element.title = station.name;
      element.style.pointerEvents = "none";

      const marker = new Marker({
        element,
        anchor: "center",
      })
        .setLngLat([station.lng, station.lat])
        .addTo(mapInstance);

      routeMarkers.current.push(marker);
    });

    return () => {
      removeMarkers(routeMarkers.current);
    };
  }, [route]);

  /*
   * =====================================
   * ОТРИСОВКА ВЫБРАННОГО МАРШРУТА
   * =====================================
   */
  useEffect(() => {
    const mapInstance = map.current;

    if (!mapInstance) {
      return;
    }

    const removeRouteLayers = () => {
      for (const layerId of [
        TRANSFER_LAYER_ID,
        TRANSFER_HALO_LAYER_ID,
        ROUTE_LAYER_ID,
        ROUTE_HALO_LAYER_ID,
      ]) {
        if (mapInstance.getLayer(layerId)) {
          mapInstance.removeLayer(layerId);
        }
      }

      for (const sourceId of [
        TRANSFER_SOURCE_ID,
        ROUTE_SOURCE_ID,
      ]) {
        if (mapInstance.getSource(sourceId)) {
          mapInstance.removeSource(sourceId);
        }
      }
    };

    const fitRoute = () => {
      if (!route || route.stations.length === 0) {
        return;
      }

      if (route.stations.length === 1) {
        const station = route.stations[0];
        mapInstance.flyTo({
          center: [station.lng, station.lat],
          zoom: 14,
          duration: 700,
          essential: true,
        });
        return;
      }

      let minLng = Infinity;
      let minLat = Infinity;
      let maxLng = -Infinity;
      let maxLat = -Infinity;

      for (const station of route.stations) {
        minLng = Math.min(minLng, station.lng);
        minLat = Math.min(minLat, station.lat);
        maxLng = Math.max(maxLng, station.lng);
        maxLat = Math.max(maxLat, station.lat);
      }

      if (
        Math.abs(maxLng - minLng) < 0.00001 &&
        Math.abs(maxLat - minLat) < 0.00001
      ) {
        mapInstance.flyTo({
          center: [minLng, minLat],
          zoom: 14,
          duration: 700,
          essential: true,
        });
        return;
      }

      mapInstance.fitBounds(
        [
          [minLng, minLat],
          [maxLng, maxLat],
        ],
        {
          padding: isMobileViewport()
            ? { top: 72, right: 34, bottom: 165, left: 34 }
            : { top: 80, right: 70, bottom: 210, left: 70 },
          maxZoom: 14,
          duration: 800,
          essential: true,
        }
      );
    };

    const drawRoute = () => {
      removeRouteLayers();

      if (!route || route.stations.length === 0) {
        return;
      }

      const rideFeatures = route.segments
        .filter((segment) => segment.stations.length >= 2)
        .map((segment) => ({
          type: "Feature" as const,
          properties: {
            color: segment.color,
            lineId: segment.lineId,
            line: segment.line,
          },
          geometry: {
            type: "LineString" as const,
            coordinates: segment.stations.map((station) => [
              station.lng,
              station.lat,
            ]),
          },
        }));

      if (rideFeatures.length > 0) {
        mapInstance.addSource(ROUTE_SOURCE_ID, {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: rideFeatures,
          },
        });

        // Белый halo отделяет маршрут от OSM и остальных линий.
        mapInstance.addLayer({
          id: ROUTE_HALO_LAYER_ID,
          type: "line",
          source: ROUTE_SOURCE_ID,
          layout: {
            "line-cap": "round",
            "line-join": "round",
          },
          paint: {
            "line-color": "#ffffff",
            "line-width": 11,
            "line-opacity": 0.95,
          },
        });

        mapInstance.addLayer({
          id: ROUTE_LAYER_ID,
          type: "line",
          source: ROUTE_SOURCE_ID,
          layout: {
            "line-cap": "round",
            "line-join": "round",
          },
          paint: {
            "line-color": ["get", "color"],
            "line-width": 7,
            "line-opacity": 1,
          },
        });
      }

      const transferFeatures = route.transfers.map(
        (transfer) => ({
          type: "Feature" as const,
          properties: {
            minutes: transfer.minutes,
          },
          geometry: {
            type: "LineString" as const,
            coordinates: [
              [transfer.from.lng, transfer.from.lat],
              [transfer.to.lng, transfer.to.lat],
            ],
          },
        })
      );

      if (transferFeatures.length > 0) {
        mapInstance.addSource(TRANSFER_SOURCE_ID, {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: transferFeatures,
          },
        });

        mapInstance.addLayer({
          id: TRANSFER_HALO_LAYER_ID,
          type: "line",
          source: TRANSFER_SOURCE_ID,
          layout: {
            "line-cap": "round",
            "line-join": "round",
          },
          paint: {
            "line-color": "#ffffff",
            "line-width": 8,
            "line-opacity": 0.95,
          },
        });

        mapInstance.addLayer({
          id: TRANSFER_LAYER_ID,
          type: "line",
          source: TRANSFER_SOURCE_ID,
          layout: {
            "line-cap": "round",
            "line-join": "round",
          },
          paint: {
            "line-color": "#374151",
            "line-width": 4,
            "line-opacity": 0.95,
            "line-dasharray": [1.2, 1.2],
          },
        });
      }

      fitRoute();
    };

    if (mapInstance.isStyleLoaded()) {
      drawRoute();
    } else {
      mapInstance.once("load", drawRoute);
    }

    return () => {
      mapInstance.off("load", drawRoute);

      try {
        removeRouteLayers();
      } catch {
        // Карта уже могла быть уничтожена при размонтировании.
      }
    };
  }, [route]);

  /*
   * =====================================
   * ПОКАЗ / СКРЫТИЕ ПОЛНОЙ СЕТИ МЕТРО
   * =====================================
   */
  useEffect(() => {
    applyMetroVisibility(metroVisible);
  }, [applyMetroVisibility, metroVisible]);

  const handleLocateUser = () => {
    if (!map.current) {
      return;
    }

    map.current.flyTo({
      center: [userLocation.lng, userLocation.lat],
      zoom: 14,
      duration: 800,
      essential: true,
    });
  };

  const handleMetroToggle = () => {
    applyMetroVisibility(!metroVisibleRef.current);
  };

  return (
    <div className="map-shell">
      <div
        ref={mapContainer}
        className="map"
      />

      <button
        type="button"
        className="map-control map-control--locate"
        onClick={handleLocateUser}
        title="Моё местоположение"
        aria-label="Моё местоположение"
      >
        📍
      </button>

      <button
        type="button"
        className={`map-control map-control--metro ${
          metroVisible ? "map-control--active" : ""
        }`}
        onClick={handleMetroToggle}
        title={
          metroVisible ? "Скрыть метро" : "Показать метро"
        }
        aria-label={
          metroVisible ? "Скрыть метро" : "Показать метро"
        }
      >
        🚇
      </button>
    </div>
  );
}
