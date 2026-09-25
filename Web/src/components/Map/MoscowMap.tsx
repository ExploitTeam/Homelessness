import { useEffect, useRef, useState } from "react";

import {
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  AttributionControl,
  setWorkerUrl,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import type {
  Hostel,
  UserLocation,
} from "../../types";

import type {
  MetroRoute,
} from "../../utils/metro";

import {
  metroLines,
} from "../../data/metroData";

setWorkerUrl(
  "/maplibre/maplibre-gl-worker.mjs"
);

interface MoscowMapProps {
  hostels: Hostel[];
  userLocation: UserLocation;
  onHostelClick: (
    hostel: Hostel
  ) => void;
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
  const mapContainer =
    useRef<HTMLDivElement | null>(null);

  const map =
    useRef<MapLibreMap | null>(null);

  const markers =
    useRef<Marker[]>([]);

  const metroMarkers =
    useRef<Marker[]>([]);

  const [metroVisible, setMetroVisible] =
    useState(false);

  const metroVisibleRef =
    useRef(false);

  const applyMetroVisibility = (
    visible: boolean
  ) => {
    metroVisibleRef.current = visible;
    setMetroVisible(visible);

    const mapInstance = map.current;

    if (!mapInstance) {
      return;
    }

    if (
      mapInstance.getLayer(
        "metro-network-line"
      )
    ) {
      mapInstance.setLayoutProperty(
        "metro-network-line",
        "visibility",
        visible
          ? "visible"
          : "none"
      );
    }

    metroMarkers.current.forEach(
      (marker) => {
        marker
          .getElement()
          .style.display = visible
          ? "flex"
          : "none";
      }
    );
  };

  /*
   * =====================================
   * СОЗДАНИЕ КАРТЫ
   * =====================================
   */

  useEffect(() => {
    if (!mapContainer.current) {
      return;
    }

    if (map.current) {
      return;
    }

    const newMap =
      new MapLibreMap({
        container:
          mapContainer.current,

        center: [
          37.6173,
          55.7558,
        ],

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

    /*
     * =====================================
     * МЕТРО
     * =====================================
     */

    newMap.on("load", () => {
      if (
        newMap.getSource(
          "metro-network"
        )
      ) {
        return;
      }

      const features =
        metroLines
          .filter(
            (line) =>
              Array.isArray(
                line.stations
              ) &&
              line.stations.length >= 2
          )
          .map((line) => ({
            type: "Feature" as const,

            properties: {
              color: line.color,
              name: line.name,
            },

            geometry: {
              type: "LineString" as const,

              coordinates:
                line.stations.map(
                  (station) => [
                    station[2],
                    station[1],
                  ] as [
                    number,
                    number
                  ]
                ),
            },
          }));

      newMap.addSource(
        "metro-network",
        {
          type: "geojson",

          data: {
            type: "FeatureCollection",
            features,
          },
        }
      );

      newMap.addLayer({
        id: "metro-network-line",

        type: "line",

        source:
          "metro-network",

        layout: {
          visibility: "none",
        },

        paint: {
          "line-color": [
            "get",
            "color",
          ],

          "line-width": 4,

          "line-opacity": 0.9,
        },
      });

      /*
       * =====================================
       * СОБИРАЕМ СТАНЦИИ
       * =====================================
       */

      const stationMap =
        new globalThis.Map<
          string,
          MetroStationView
        >();

      for (
        const line of metroLines
      ) {
        for (
          const station of line.stations
        ) {
          const name =
            station[0];

          const lat =
            station[1];

          const lng =
            station[2];

          if (
            typeof lat !== "number" ||
            typeof lng !== "number" ||
            !Number.isFinite(lat) ||
            !Number.isFinite(lng)
          ) {
            continue;
          }

          const key =
            `${name}_${lat.toFixed(
              5
            )}_${lng.toFixed(5)}`;

          const existing =
            stationMap.get(key);

          if (existing) {
            if (
              !existing.colors.includes(
                line.color
              )
            ) {
              existing.colors.push(
                line.color
              );
            }
          } else {
            stationMap.set(
              key,
              {
                name,
                lat,
                lng,
                colors: [
                  line.color,
                ],
              }
            );
          }
        }
      }

      /*
       * =====================================
       * МАРКЕРЫ СТАНЦИЙ
       * =====================================
       */

      stationMap.forEach(
        (
          station
        ) => {
          const element =
            document.createElement(
              "div"
            );

          element.className =
            "metro-station-marker";

          element.style.width =
            "14px";

          element.style.height =
            "14px";

          element.style.borderRadius =
            "50%";

          element.style.border =
            "2px solid white";

          element.style.boxSizing =
            "border-box";

          element.style.cursor =
            "pointer";

          element.style.display =
            metroVisibleRef.current
              ? "flex"
              : "none";

          element.style.boxShadow =
            "0 1px 5px rgba(0,0,0,0.35)";

          /*
           * Станция одной линии
           */

          if (
            station.colors.length ===
            1
          ) {
            element.style.background =
              station.colors[0];
          } else {
            /*
             * Пересадочная станция
             */

            const sectors =
              station.colors.map(
                (
                  color,
                  index
                ) => {
                  const start =
                    (index /
                      station.colors
                        .length) *
                    100;

                  const end =
                    ((index + 1) /
                      station.colors
                        .length) *
                    100;

                  return `${color} ${start}% ${end}%`;
                }
              );

            element.style.background =
              `conic-gradient(${sectors.join(
                ", "
              )})`;
          }

          element.title =
            station.name;

          const marker =
            new Marker({
              element,
              anchor:
                "center",
            })
              .setLngLat([
                station.lng,
                station.lat,
              ])
              .addTo(newMap);

          metroMarkers.current.push(
            marker
          );
        }
      );

      /*
       * Применяем текущее состояние метро
       */

      applyMetroVisibility(
        metroVisibleRef.current
      );
    });

    return () => {
      metroMarkers.current.forEach(
        (marker) => {
          marker.remove();
        }
      );

      markers.current.forEach(
        (marker) => {
          marker.remove();
        }
      );

      metroMarkers.current = [];
      markers.current = [];

      newMap.remove();

      map.current = null;
    };
  }, []);

  /*
   * =====================================
   * МАРКЕРЫ ПОЛЬЗОВАТЕЛЯ И НОЧЛЕЖЕК
   * =====================================
   */

  useEffect(() => {
    if (!map.current) {
      return;
    }

    markers.current.forEach(
      (marker) => {
        marker.remove();
      }
    );

    markers.current = [];

    /*
     * Пользователь
     */

    const userElement =
      document.createElement(
        "div"
      );

    userElement.style.width =
      "18px";

    userElement.style.height =
      "18px";

    userElement.style.borderRadius =
      "50%";

    userElement.style.background =
      "#2563eb";

    userElement.style.border =
      "4px solid white";

    userElement.style.boxSizing =
      "border-box";

    userElement.style.boxShadow =
      "0 2px 10px rgba(0,0,0,0.35)";

    const userMarker =
      new Marker({
        element:
          userElement,
        anchor:
          "center",
      })
        .setLngLat([
          userLocation.lng,
          userLocation.lat,
        ])
        .addTo(map.current);

    markers.current.push(
      userMarker
    );

    /*
     * Ночлежки
     */

    for (
      const hostel of hostels
    ) {
      if (
        !Number.isFinite(
          hostel.lat
        ) ||
        !Number.isFinite(
          hostel.lng
        )
      ) {
        continue;
      }

      const element =
        document.createElement(
          "button"
        );

      element.type =
        "button";

      element.style.width =
        "38px";

      element.style.height =
        "38px";

      element.style.borderRadius =
        "50%";

      element.style.border =
        "3px solid white";

      element.style.background =
        hostel.isWorking
          ? "#ef4444"
          : "#6b7280";

      element.style.boxShadow =
        "0 2px 10px rgba(0,0,0,0.35)";

      element.style.cursor =
        "pointer";

      element.style.color =
        "white";

      element.style.fontSize =
        "18px";

      element.style.display =
        "flex";

      element.style.alignItems =
        "center";

      element.style.justifyContent =
        "center";

      element.innerText =
        "⌂";

      element.title =
        hostel.name;

      element.addEventListener(
        "click",
        () => {
          onHostelClick(
            hostel
          );
        }
      );

      const marker =
        new Marker({
          element,
          anchor:
            "center",
        })
          .setLngLat([
            hostel.lng,
            hostel.lat,
          ])
          .addTo(
            map.current
          );

      markers.current.push(
        marker
      );
    }

    /*
     * Станции выбранного маршрута
     */

    if (route) {
      for (
        const station of route.stations
      ) {
        const element =
          document.createElement(
            "div"
          );

        element.style.width =
          "28px";

        element.style.height =
          "28px";

        element.style.borderRadius =
          "50%";

        element.style.background =
          "#111827";

        element.style.border =
          "3px solid white";

        element.style.boxShadow =
          "0 2px 8px rgba(0,0,0,0.3)";

        element.style.display =
          "flex";

        element.style.alignItems =
          "center";

        element.style.justifyContent =
          "center";

        element.style.color =
          "white";

        element.style.fontSize =
          "14px";

        element.innerText =
          "🚇";

        element.title =
          station.name;

        const marker =
          new Marker({
            element,
            anchor:
              "center",
          })
            .setLngLat([
              station.lng,
              station.lat,
            ])
            .addTo(
              map.current
            );

        markers.current.push(
          marker
        );
      }
    }
  }, [
    hostels,
    userLocation,
    onHostelClick,
    route,
  ]);

  /*
   * =====================================
   * ЛИНИЯ ВЫБРАННОГО МАРШРУТА
   * =====================================
   */

  useEffect(() => {
    if (!map.current) {
      return;
    }

    const mapInstance =
      map.current;

    const sourceId =
      "selected-metro-route";

    const layerId =
      "selected-metro-route-line";

    const drawRoute =
      () => {
        /*
         * Удаляем старую линию
         */

        if (
          mapInstance.getLayer(
            layerId
          )
        ) {
          mapInstance.removeLayer(
            layerId
          );
        }

        if (
          mapInstance.getSource(
            sourceId
          )
        ) {
          mapInstance.removeSource(
            sourceId
          );
        }

        /*
         * Если маршрута нет —
         * ничего не рисуем
         */

        if (
          !route ||
          route.stations.length < 2
        ) {
          return;
        }

        const coordinates =
          route.stations.map(
            (station) => [
              station.lng,
              station.lat,
            ] as [
              number,
              number
            ]
          );

        /*
         * Добавляем GeoJSON
         */

        mapInstance.addSource(
          sourceId,
          {
            type: "geojson",

            data: {
              type: "Feature",

              properties: {},

              geometry: {
                type: "LineString",

                coordinates,
              },
            },
          }
        );

        /*
         * Добавляем линию маршрута
         */

        mapInstance.addLayer({
          id: layerId,

          type: "line",

          source: sourceId,

          paint: {
            "line-color":
              "#2563eb",

            "line-width": 7,

            "line-opacity": 0.95,
          },
        });
      };

    if (
      mapInstance.isStyleLoaded()
    ) {
      drawRoute();
    } else {
      mapInstance.once(
        "load",
        drawRoute
      );
    }

    return () => {
      if (
        mapInstance.getLayer(
          layerId
        )
      ) {
        mapInstance.removeLayer(
          layerId
        );
      }

      if (
        mapInstance.getSource(
          sourceId
        )
      ) {
        mapInstance.removeSource(
          sourceId
        );
      }
    };
  }, [route]);

  /*
   * =====================================
   * ПОКАЗ / СКРЫТИЕ МЕТРО
   * =====================================
   */

  useEffect(() => {
    if (!map.current) {
      return;
    }

    const mapInstance =
      map.current;

    const updateVisibility =
      () => {
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

        metroMarkers.current.forEach(
          (marker) => {
            marker
              .getElement()
              .style.display =
              metroVisible
                ? "flex"
                : "none";
          }
        );
      };

    if (
      mapInstance.isStyleLoaded()
    ) {
      updateVisibility();
    } else {
      mapInstance.once(
        "load",
        updateVisibility
      );
    }
  }, [metroVisible]);

  /*
   * =====================================
   * ПЕРЕЙТИ К ПОЛЬЗОВАТЕЛЮ
   * =====================================
   */

  const handleLocateUser =
    () => {
      if (!map.current) {
        return;
      }

      map.current.flyTo({
        center: [
          userLocation.lng,
          userLocation.lat,
        ],

        zoom: 14,

        duration: 1000,

        essential: true,
      });
    };

  /*
   * =====================================
   * КНОПКА МЕТРО
   * =====================================
   */

  const handleMetroToggle =
    () => {
      applyMetroVisibility(
        !metroVisibleRef.current
      );
    };

  return (
    <div
      style={{
        position:
          "relative",

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

      /*
       * Кнопка местоположения
       */

      <button
        type="button"
        onClick={
          handleLocateUser
        }
        title="Моё местоположение"
        aria-label="Моё местоположение"
        style={{
          position:
            "absolute",

          top: "72px",

          left: "16px",

          zIndex: 10,

          width: "48px",

          height: "48px",

          border: "none",

          borderRadius:
            "14px",

          background:
            "rgba(255,255,255,0.96)",

          boxShadow:
            "0 3px 12px rgba(0,0,0,0.2)",

          fontSize: "24px",

          cursor:
            "pointer",

          display: "flex",

          alignItems:
            "center",

          justifyContent:
            "center",
        }}
      >
        📍
      </button>

      /*
       * Кнопка метро
       */

      <button
        type="button"
        onClick={
          handleMetroToggle
        }
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
          position:
            "absolute",

          top: "128px",

          left: "16px",

          zIndex: 10,

          width: "48px",

          height: "48px",

          border: "none",

          borderRadius:
            "14px",

          background:
            metroVisible
              ? "#111827"
              : "rgba(255,255,255,0.96)",

          color:
            metroVisible
              ? "#ffffff"
              : "#111827",

          boxShadow:
            "0 3px 12px rgba(0,0,0,0.2)",

          fontSize: "24px",

          cursor:
            "pointer",

          display: "flex",

          alignItems:
            "center",

          justifyContent:
            "center",
        }}
      >
        🚇
      </button>
    </div>
  );
}