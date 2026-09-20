import { useCallback, useState } from "react";

import MoscowMap from "./components/Map/MoscowMap";
import HostelCard from "./components/HostelCard/HostelCard";

import { useUserLocation } from "./hooks/useUserLocation";
import { useHostels } from "./hooks/useHostels";

import type { Hostel } from "./types";
import { mockUserLocation } from "./data/mockData";

function App() {
  const [selectedHostel, setSelectedHostel] =
    useState<Hostel | null>(null);

  const { location } = useUserLocation();

  // Если геолокация ещё недоступна то
  // используем Москву как запасной вариант
  const mapLocation = location ?? mockUserLocation;

  const {
    hostels,
    loading: hostelsLoading,
    error: hostelsError,
  } = useHostels(mapLocation);

  const handleHostelClick = useCallback(
    (hostel: Hostel) => {
      setSelectedHostel(hostel);
    },
    []
  );

  const handleCloseCard = useCallback(() => {
    setSelectedHostel(null);
  }, []);

  return (
    <div className="app">
      <MoscowMap
        hostels={hostels}
        userLocation={mapLocation}
        onHostelClick={handleHostelClick}
      />

      {hostelsLoading && (
        <div className="map-status">
          Загружаем ночлежки...
        </div>
      )}

      {hostelsError && (
        <div className="map-error">
          {hostelsError}
        </div>
      )}

      {selectedHostel && (
        <HostelCard
          hostel={selectedHostel}
          userLocation={mapLocation}
          onClose={handleCloseCard}
        />
      )}
    </div>
  );
}

export default App;