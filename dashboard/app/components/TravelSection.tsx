"use client";

import { useMemo } from "react";
import { TravelData, Trip, Flight } from "../types";

function formatDate(dateStr: string) {
  if (!dateStr) return "";
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatDateShort(dateStr: string) {
  if (!dateStr) return "";
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function TripTimeline({ trips }: { trips: Trip[] }) {
  if (trips.length === 0) return null;

  // Sort by departure date
  const sorted = [...trips].sort((a, b) => a.departureDate.localeCompare(b.departureDate));

  return (
    <div className="space-y-4">
      {sorted.map((trip) => {
        const isOngoing = !trip.returnDate;
        return (
          <div
            key={trip.tripId}
            className="relative pl-8 pb-4 border-l-2 border-[var(--border)] last:border-l-0"
          >
            {/* Timeline dot */}
            <div className="absolute left-[-7px] top-1 w-3 h-3 rounded-full bg-blue-500" />

            <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)]">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h4 className="text-lg font-medium">
                    {trip.destinationCity}
                    {trip.destinationCountry && (
                      <span className="text-[var(--subtle)] font-normal">, {trip.destinationCountry}</span>
                    )}
                  </h4>
                  <p className="text-sm text-[var(--subtle)]">
                    {formatDate(trip.departureDate)}
                    {trip.returnDate ? ` — ${formatDate(trip.returnDate)}` : " — ongoing"}
                  </p>
                </div>
                <span className="text-xs px-2 py-1 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 whitespace-nowrap">
                  {trip.purpose}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <p className="text-xs text-[var(--subtle)]">Duration</p>
                  <p className="font-medium">{trip.durationDays} days</p>
                </div>
                <div>
                  <p className="text-xs text-[var(--subtle)]">Flights</p>
                  <p className="font-medium">{trip.flightCount}</p>
                </div>
                <div>
                  <p className="text-xs text-[var(--subtle)]">Miles</p>
                  <p className="font-medium">{trip.totalMiles.toLocaleString()}</p>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FlightLog({ flights }: { flights: Flight[] }) {
  if (flights.length === 0) return null;

  const sorted = [...flights].sort((a, b) => a.flightDate.localeCompare(b.flightDate));

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--subtle)]">
            <th className="pb-2 pr-4 font-medium">Date</th>
            <th className="pb-2 pr-4 font-medium">Route</th>
            <th className="pb-2 pr-4 font-medium">Flight</th>
            <th className="pb-2 pr-4 font-medium text-right">Miles</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((flight, i) => (
            <tr key={i} className="border-b border-[var(--border)]/50">
              <td className="py-2 pr-4 text-[var(--subtle)]">{formatDateShort(flight.flightDate)}</td>
              <td className="py-2 pr-4">
                <span className="font-mono font-medium">{flight.origin}</span>
                <span className="text-[var(--subtle)] mx-1">→</span>
                <span className="font-mono font-medium">{flight.destination}</span>
              </td>
              <td className="py-2 pr-4 text-[var(--subtle)]">{flight.flightNumber}</td>
              <td className="py-2 pr-4 text-right font-mono">{flight.miles.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TravelSection({ travel }: { travel: TravelData }) {
  const stats = useMemo(() => {
    const totalMiles = travel.flights.reduce((sum, f) => sum + f.miles, 0);
    const totalFlights = travel.flights.length;
    const totalTrips = travel.trips.length;
    const totalDays = travel.trips.reduce((sum, t) => sum + t.durationDays, 0);
    const destinations = new Set(travel.trips.map((t) => t.destinationCity)).size;
    const countries = new Set(
      travel.trips.map((t) => t.destinationCountry).filter(Boolean)
    ).size;

    // Earth circumference ~24,901 miles
    const earthLaps = totalMiles / 24901;

    return { totalMiles, totalFlights, totalTrips, totalDays, destinations, countries, earthLaps };
  }, [travel]);

  if (travel.trips.length === 0 && travel.flights.length === 0) {
    return null;
  }

  return (
    <section className="border-t border-[var(--border)] pt-8">
      <h2 className="text-2xl font-medium mb-6">Travel</h2>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-xs text-[var(--subtle)]">Trips</p>
          <p className="text-lg font-medium">{stats.totalTrips}</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-xs text-[var(--subtle)]">Days Traveling</p>
          <p className="text-lg font-medium">{stats.totalDays}</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-xs text-[var(--subtle)]">Flights</p>
          <p className="text-lg font-medium">{stats.totalFlights}</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-xs text-[var(--subtle)]">Miles Flown</p>
          <p className="text-lg font-medium">{stats.totalMiles.toLocaleString()}</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-xs text-[var(--subtle)]">Destinations</p>
          <p className="text-lg font-medium">{stats.destinations}</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-xs text-[var(--subtle)]">Around the Earth</p>
          <p className="text-lg font-medium">{stats.earthLaps.toFixed(1)}x</p>
        </div>
      </div>

      {/* Trip timeline */}
      <div className="mb-8">
        <h3 className="text-lg font-medium mb-4">Trips</h3>
        <TripTimeline trips={travel.trips} />
      </div>

      {/* Flight log */}
      <div>
        <h3 className="text-lg font-medium mb-4">Flight Log</h3>
        <FlightLog flights={travel.flights} />
      </div>
    </section>
  );
}
