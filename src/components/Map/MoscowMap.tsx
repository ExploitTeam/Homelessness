import { useEffect, useRef } from "react";

import {
  Map,
  Marker,
  NavigationControl,
  AttributionControl,
  setWorkerUrl,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import type { Hostel, UserLocation } from "../../types";

setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

interface MoscowMapProps {
  hostels: Hostel[];
  userLocation: UserLocation;
  onHostelClick: (hostel: Hostel) => void;
}

export default function MoscowMap({
  hostels,
  userLocation,
  onHostelClick,
}: MoscowMapProps) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const map = useRef<Map | null>(null);
  const markers = useRef<Marker[]>([]);
  // создание картыв
  useEffect(() => {
    if (!mapContainer.current) {
      return;
    }

    if (map.current) {
      return;
    }

    const newMap = new Map({
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

            attribution:
              "© OpenStreetMap contributors",
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

    return () => {
      newMap.remove();
      map.current = null;
    };
  }, []);

  // Перемещаем карту к пользователю
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

  // Создаём маркеры
  useEffect(() => {
    if (!map.current) {
      return;
    }
    // Удалеиние старые маркеров
    markers.current.forEach((marker) => {
      marker.remove()
    });

    markers.current = [];

    // Точка пользователя
    const userElement = document.createElement("div");

    userElement.className = "user-marker";

    const userMarker = new Marker({
      element: userElement,
    })
      .setLngLat([
        userLocation.lng,
        userLocation.lat
      ])
      .addTo(map.current);

    markers.current.push(userMarker);
  
    // Ночлежки
    hostels.forEach((hostel) => {
      const element = document.createElement("div");

      element.className = "hostel-marker";
      element.innerText = "🏠";
      element.title = hostel.name;

      element.addEventListener("click", () => {
        onHostelClick(hostel);
      });

      const hostelMarker = new Marker({
        element,
      })
        .setLngLat([
          hostel.lng,
          hostel.lat
        ])
        .addTo(map.current!);

        markers.current.push(hostelMarker);
    });
  }, [
    hostels,
    userLocation,
    onHostelClick,
  ]);

  return (
    <div
      ref={mapContainer}
      className="map"
      style={{
        width: "100%",
        height: "100vh",
      }}
    />
  );
}