import { useEffect, useRef, useState } from "react";

import {
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  AttributionControl,
  setWorkerUrl,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import type { Hostel, UserLocation } from "../../types";
import type { MetroRoute } from "../../utils/metro";
import { metroLines } from "../../data/metroData";

setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

interface MoscowMapProps {
  hostels: Hostel[];
  userLocation: UserLocation;
  onHostelClick: (hostel: Hostel) => void;
  route: MetroRoute | null;
}

interface MetroStationView {
  name: string;
  lat: number;
  lng: number;
  colors: string[];
}

export default function MoscowMap({
  hostels,
  userLocation,
  onHostelClick,
  route,
}: MoscowMapProps) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);

  const markers = useRef<Marker[]>([]);
  const metroMarkers = useRef<Marker[]>([]);

  const [metroVisible, setMetroVisible] = useState(true);

  // Создание карты
  useEffect(() => {
    if (!mapContainer.current) {
      return;
    }

    if (map.current) {
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
      new NavigationControl(),
      "top-right"
    );

    newMap.addControl(
      new AttributionControl(),
      "bottom-right"
    );

    newMap.on("load", () => {
      // Линии метро
      const features = metroLines.map((line) => ({
        type: "Feature" as const,
        properties: {
          color: line.color,
          name: line.name,
        },
        geometry: {
          type: "LineString" as const,
          coordinates: line.stations.map((station) => [
            station[2],
            station[1],
          ]),
        },
      }));

      newMap.addSource("metro-network", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features,
        },
      });

      newMap.addLayer({
        id: "metro-network-line",
        type: "line",
        source: "metro-network",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 4,
          "line-opacity": 0.85,
        },
      });

      // Станции метро
      const stationMap = new globalThis.Map<
        string,
        MetroStationView
      >();

      for (const line of metroLines) {
        for (const station of line.stations) {
          const name = station[0];
          const lat = station[1];
          const lng = station[2];

          const key = `${name}_${lat.toFixed(
            5
          )}_${lng.toFixed(5)}`;

          const existing = stationMap.get(key);

          if (existing) {
            if (!existing.colors.includes(line.color)) {
              existing.colors.push(line.color);
            }
          } else {
            stationMap.set(key, {
              name,
              lat,
              lng,
              colors: [line.color],
            });
          }
        }
      }

      stationMap.forEach((station) => {
        const element = document.createElement("div");

        element.className = "metro-station-marker";

        element.style.width = "11px";
        element.style.height = "11px";
        element.style.borderRadius = "50%";
        element.style.border = "2px solid white";
        element.style.boxShadow =
          "0 1px 5px rgba(0,0,0,0.35)";
        element.style.cursor = "pointer";

        if (station.colors.length === 1) {
          element.style.background = station.colors[0];
        } else {
          const sectors = station.colors.map(
            (color, index) => {
              const start =
                (index / station.colors.length) * 100;

              const end =
                ((index + 1) /
                  station.colors.length) *
                100;

              return `${color} ${start}% ${end}%`;
            }
          );

          element.style.background =
            `conic-gradient(${sectors.join(", ")})`;
        }

        element.title = station.name;

        const marker = new Marker({
          element,
        })
          .setLngLat([
            station.lng,
            station.lat,
          ])
          .addTo(newMap);

        metroMarkers.current.push(marker);
      });
    });

    return () => {
      metroMarkers.current.forEach((marker) => {
        marker.remove();
      });

      metroMarkers.current = [];

      newMap.remove();
      map.current = null;
    };
  }, []);

  // Перемещение карты к пользователю
  useEffect(() => {
    if (!map.current) {
      return;
    }

    map.current.flyTo({
      center: [
        userLocation.lng,
        userLocation.lat,
      ],
      zoom: 13,
      duration: 1000,
    });
  }, [userLocation]);

  // Маркеры пользователя и ночлежек
  useEffect(() => {
    if (!map.current) {
      return;
    }

    markers.current.forEach((marker) => {
      marker.remove();
    });

    markers.current = [];

    // Пользователь
    const userElement = document.createElement("div");

    userElement.className = "user-marker";
    userElement.style.width = "18px";
    userElement.style.height = "18px";
    userElement.style.borderRadius = "50%";
    userElement.style.background = "#2563eb";
    userElement.style.border = "4px solid white";
    userElement.style.boxShadow =
      "0 2px 8px rgba(0,0,0,0.35)";

    const userMarker = new Marker({
      element: userElement,
    })
      .setLngLat([
        userLocation.lng,
        userLocation.lat,
      ])
      .addTo(map.current);

    markers.current.push(userMarker);

    // Ночлежки
    console.log(
      "HOSTELS RECEIVED BY MAP:",
      hostels
    );

    for (const hostel of hostels) {
      console.log(
        "CREATING HOSTEL MARKER:",
        hostel.id,
        hostel.name,
        hostel.lat,
        hostel.lng
      );

      const element = document.createElement("div");

      element.className = "hostel-marker";
      element.innerText = "🏠";

      element.style.width = "38px";
      element.style.height = "38px";
      element.style.display = "flex";
      element.style.alignItems = "center";
      element.style.justifyContent = "center";
      element.style.borderRadius = "50%";
      element.style.background = "white";
      element.style.boxShadow =
        "0 2px 9px rgba(0,0,0,0.3)";
      element.style.fontSize = "22px";
      element.style.cursor = "pointer";

      element.title = hostel.name;

      element.addEventListener("click", () => {
        onHostelClick(hostel);
      });

      const marker = new Marker({
        element,
      })
        .setLngLat([
          hostel.lng,
          hostel.lat,
        ])
        .addTo(map.current);

      markers.current.push(marker);
    }

    // Станции выбранного маршрута
    if (route) {
      for (const station of route.stations) {
        const element = document.createElement("div");

        element.className = "metro-route-marker";
        element.innerText = "🚇";

        element.style.width = "30px";
        element.style.height = "30px";
        element.style.display = "flex";
        element.style.alignItems = "center";
        element.style.justifyContent = "center";
        element.style.borderRadius = "50%";
        element.style.background = "white";
        element.style.boxShadow =
          "0 2px 8px rgba(0,0,0,0.3)";
        element.style.fontSize = "17px";

        element.title = station.name;

        const marker = new Marker({
          element,
        })
          .setLngLat([
            station.lng,
            station.lat,
          ])
          .addTo(map.current);

        markers.current.push(marker);
      }
    }
  }, [
    hostels,
    userLocation,
    onHostelClick,
    route,
  ]);

  // Видимость метро
  useEffect(() => {
    if (!map.current) {
      return;
    }

    const mapInstance = map.current;

    const updateVisibility = () => {
      if (
        mapInstance.getLayer(
          "metro-network-line"
        )
      ) {
        mapInstance.setLayoutProperty(
          "metro-network-line",
          "visibility",
          metroVisible
            ? "visible"
            : "none"
        );
      }

      metroMarkers.current.forEach((marker) => {
        marker.getElement().style.display =
          metroVisible ? "flex" : "none";
      });
    };

    if (mapInstance.isStyleLoaded()) {
      updateVisibility();
    } else {
      mapInstance.once(
        "load",
        updateVisibility
      );
    }
  }, [metroVisible]);

  // Линия выбранного маршрута
  useEffect(() => {
    if (!map.current) {
      return;
    }

    const mapInstance = map.current;

    const sourceId = "selected-metro-route";
    const layerId = "selected-metro-route-line";

    const drawRoute = () => {
      if (mapInstance.getLayer(layerId)) {
        mapInstance.removeLayer(layerId);
      }

      if (mapInstance.getSource(sourceId)) {
        mapInstance.removeSource(sourceId);
      }

      if (
        !route ||
        route.stations.length < 2
      ) {
        return;
      }

      mapInstance.addSource(sourceId, {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates:
              route.stations.map((station) => [
                station.lng,
                station.lat,
              ]),
          },
        },
      });

      mapInstance.addLayer({
        id: layerId,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#2563eb",
          "line-width": 7,
          "line-opacity": 0.95,
        },
      });
    };

    if (mapInstance.isStyleLoaded()) {
      drawRoute();
    } else {
      mapInstance.once("load", drawRoute);
    }

    return () => {
      if (mapInstance.getLayer(layerId)) {
        mapInstance.removeLayer(layerId);
      }

      if (mapInstance.getSource(sourceId)) {
        mapInstance.removeSource(sourceId);
      }
    };
  }, [route]);

  const handleMetroToggle = () => {
    setMetroVisible((current) => !current);
  };

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100dvh",
      }}
    >
      <div
        ref={mapContainer}
        className="map"
        style={{
          width: "100%",
          height: "100%",
        }}
      />

      <button
        type="button"
        className="metro-toggle"
        onClick={handleMetroToggle}
        title={
          metroVisible
            ? "Скрыть метро"
            : "Показать метро"
        }
        aria-label={
          metroVisible
            ? "Скрыть метро"
            : "Показать метро"
        }
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          zIndex: 10,
          width: "48px",
          height: "48px",
          border: "none",
          borderRadius: "14px",
          background:
            "rgba(255,255,255,0.96)",
          boxShadow:
            "0 3px 12px rgba(0,0,0,0.2)",
          fontSize: "24px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: metroVisible ? 1 : 0.55,
        }}
      >
        🚇
      </button>
    </div>
  );
}