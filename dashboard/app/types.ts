export interface DayData {
  date: string; // YYYY-MM-DD
  habits: {
    workout: "cardio" | "weights" | "both" | null;
    sauna: boolean;
    meditation: boolean;
  };
  sleep: number | null; // hours
  restingHR: number | null; // bpm
  stress: "low" | "moderate" | "high" | null;
  location: string | null;
  notes: string | null;
  timeWithArno: number | null; // minutes
  timeWorking: number | null; // minutes
  timeCoding: number | null; // minutes
  // Extended fields from pipeline
  sleepScore: number | null;
  readinessScore: number | null;
  activityScore: number | null;
  steps: number | null;
  activeCalories: number | null;
  sleepDeepMin: number | null;
  sleepRemMin: number | null;
  weatherHighF: number | null;
  weatherCondition: string | null;
  mood: number | null;
  energy: number | null;
}

export interface Trip {
  tripId: string;
  departureDate: string;
  returnDate: string;
  destinationCity: string;
  destinationCountry: string;
  purpose: string;
  durationDays: number;
  totalMiles: number;
  flightCount: number;
}

export interface Flight {
  flightDate: string;
  tripId: string;
  origin: string;
  destination: string;
  airline: string;
  flightNumber: string;
  miles: number;
}

export interface TravelData {
  trips: Trip[];
  flights: Flight[];
}

export interface TrackerData {
  days: Record<string, DayData>;
  travel?: TravelData;
  generated: string;
}
