import { useEffect, useState } from "/releases/v5-20261019/vendor/react-vendor.mjs";
export function useUserLocation() {
    const [location, setLocation] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        if (!navigator.geolocation) {
            setError("Браузер не поддерживает определение местоположения");
            setLoading(false);
            return;
        }
        const watchId = navigator.geolocation.watchPosition((position) => {
            setLocation({
                lat: position.coords.latitude,
                lng: position.coords.longitude,
            });
            setLoading(false);
            setError(null);
        }, (error) => {
            console.error("Ошибка определения вашего местоположения:", error);
            setError("Не удалось определить ваше местоположение");
            setLoading(false);
        }, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
        });
        return () => {
            navigator.geolocation.clearWatch(watchId);
        };
    }, []);
    return {
        location,
        loading,
        error,
    };
}
