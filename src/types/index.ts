export interface Hostel {
  id: number;
  name: string;
  address: string;
  lat: number;
  lng: number;
  bedsAvailable: number;
  bedsTotal: number;
  description: string;
  phone: string;
  email: string;
}

export interface UserLocation {
  lat: number;
  lng: number;
}