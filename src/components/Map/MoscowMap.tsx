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
    useState(true);

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

    const newMap = new MapLibreMap({
      container: mapContainer.current,

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
     * ЛИНИИ МЕТРО
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
        metroLines.map(
          (line) => ({
            type: "Feature" as const,

            properties: {
              color: line.color,
              name: line.name,
            },

            geometry: {
              type: "LineString" as const,

              coordinates:
                line.stations.map(
                  (
                    station
                  ) => [
                    station[2],
                    station[1],
                  ]
                ),
            },
          })
        );

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

        source: "metro-network",

        paint: {
          "line-color": [
            "get",
            "color",
          ],

          "line-width": 4,

          "line-opacity": 0.85,
        },
      });

      /*
       * =====================================
       * СОБИРАЕМ ВСЕ СТАНЦИИ
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
          station: MetroStationView
        ) => {
          const element =
            document.createElement(
              "div"
            );

          element.className =
            "metro-station-marker";

          /*
           * Одна линия
           */

          if (
            station.colors.length ===
            1
          ) {
            element.style.background =
              station.colors[0];
          } else {
            /*
             * Пересадка.
             * Делим кружок на сектора.
             */

            const sectors =
              station.colors.map(
                (
                  color: string,
                  index: number
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
    });

    return () => {
      metroMarkers.current.forEach(
        (marker) => {
          marker.remove();
        }
      );

      metroMarkers.current = [];

      newMap.remove();

      map.current = null;
    };
  }, []);

  /*
   * =====================================
   * ПЕРЕМЕЩЕНИЕ К ПОЛЬЗОВАТЕЛЮ
   * =====================================
   */

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

  /*
   * =====================================
   * ВКЛЮЧЕНИЕ / ВЫКЛЮЧЕНИЕ МЕТРО
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
          (
            marker: Marker
          ) => {
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
   * МАРКЕРЫ НОЧЛЕЖЕК И ПОЛЬЗОВАТЕЛЯ
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

    userElement.className =
      "user-marker";

    const userMarker =
      new Marker({
        element: userElement,
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
      const element =
        document.createElement(
          "div"
        );

      element.className =
        "hostel-marker";

      element.innerText =
        "🏠";

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

        element.className =
          "metro-route-marker";

        element.innerText =
          "🚇";

        element.title =
          station.name;

        const marker =
          new Marker({
            element,
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

        if (
          !route ||
          route.stations.length < 2
        ) {
          return;
        }

        mapInstance.addSource(
          sourceId,
          {
            type: "geojson",

            data: {
              type: "Feature",

              properties: {},

              geometry: {
                type: "LineString",

                coordinates:
                  route.stations.map(
                    (
                      station
                    ) => [
                      station.lng,
                      station.lat,
                    ]
                  ),
              },
            },
          }
        );

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
   * КНОПКА МЕТРО
   * =====================================
   */

  const handleMetroToggle =
    () => {
      setMetroVisible(
        (current) =>
          !current
      );
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
      >
        🚇
      </button>
    </div>
  );
}