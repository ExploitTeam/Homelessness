import { useCallback, useState } from "react";

import MoscowMap from "./components/Map/MoscowMap";
import HostelCard from "./components/HostelCard/HostelCard";

import { useUserLocation } from "./hooks/useUserLocation";
import { useHostels } from "./hooks/useHostels";

import type { Hostel } from "./types";

function App() {
  const [selectedHostel, setSelectedHostel] =
    useState<Hostel | null>(null);

  const {
    location,
    loading: locationLoading,
    error: locationError,
  } = useUserLocation();

  const {
    hostels,
    loading: hostelsLoading,
    error: hostelsError,
  } = useHostels(location);

  const handleHostelClick = useCallback(
    (hostel: Hostel) => {
      setSelectedHostel(hostel);
    },
    []
  );

  const handleCloseCard = useCallback(() => {
    setSelectedHostel(null);
  }, []);

  const handleBook = useCallback(() => {
    if (!selectedHostel) {
      return;
    }

    console.log(
      "Будущий запрос на сервер:",
      {
        hostelId: selectedHostel.id,
      }
    );
  }, [selectedHostel]);

  const handleContacts = useCallback(() => {
    if (!selectedHostel) {
      return;
    }

    alert(
      `Телефон: ${selectedHostel.phone}\nEmail: ${selectedHostel.email}`
    );
  }, [selectedHostel]);

  if (locationLoading) {
    return (
      <div className="loading-screen">
        Определяем ваше местоположение...
      </div>
    );
  }

  if (locationError || !location) {
    return (
      <div className="loading-screen">
        {locationError ??
          "Местоположение недоступно"}
      </div>
    );
  }

  return (
    <div className="app">
      <MoscowMap
        hostels={hostels}
        userLocation={location}
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
          onClose={handleCloseCard}
          onBook={handleBook}
          onContacts={handleContacts}
        />
      )}
    </div>
  );
}

export default App;