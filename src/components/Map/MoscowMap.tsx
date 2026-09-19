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

  useEffect(() => {
    if (!mapContainer.current) return;

    if (map.current) return;

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

    //Точка пользователя
    const userElement = document.createElement("div");

    userElement.className = "user-marker";

    new Marker({
      element: userElement,
    })
      .setLngLat([
        userLocation.lng,
        userLocation.lat,
      ])
      .addTo(newMap);

    //Ночлежки
    hostels.forEach((hostel) => {
      const element = document.createElement("div");

      element.className = "hostel-marker";
      element.innerText = "🏠";

      element.addEventListener("click", () => {
        onHostelClick(hostel);
      });

      new Marker({
        element,
      })
        .setLngLat([
          hostel.lng,
          hostel.lat,
        ])
        .addTo(newMap);
    });

    return () => {
      newMap.remove();
      map.current = null;
    };
  }, [hostels, userLocation, onHostelClick]);

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