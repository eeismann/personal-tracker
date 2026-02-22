"""Extract travel itineraries from Google Calendar events.

Parses flight events from the calendar events sheet, groups them into trips,
and calculates distances using the haversine formula with airport coordinates.
"""

import math
import os
import re
from datetime import date, timedelta
from io import StringIO

import httpx
import pandas as pd

from pipeline.config import RAW_DIR

# Major airport coordinates (lat, lon)
AIRPORTS = {
    "SFO": (37.6213, -122.3790),
    "MIA": (25.7959, -80.2870),
    "GRU": (-23.4356, -46.4731),
    "JFK": (40.6413, -73.7781),
    "LAX": (33.9425, -118.4081),
    "ORD": (41.9742, -87.9073),
    "DFW": (32.8998, -97.0403),
    "ATL": (33.6407, -84.4277),
    "DEN": (39.8561, -104.6737),
    "SEA": (47.4502, -122.3088),
    "BOS": (42.3656, -71.0096),
    "EWR": (40.6895, -74.1745),
    "IAH": (29.9902, -95.3368),
    "PHX": (33.4373, -112.0078),
    "LAS": (36.0840, -115.1537),
    "MCO": (28.4312, -81.3081),
    "CLT": (35.2144, -80.9473),
    "MSP": (44.8848, -93.2223),
    "DTW": (42.2124, -83.3534),
    "PHL": (39.8744, -75.2424),
    "DCA": (38.8512, -77.0402),
    "IAD": (38.9531, -77.4565),
    "SAN": (32.7338, -117.1933),
    "AUS": (30.1975, -97.6664),
    "PDX": (45.5898, -122.5951),
    "HNL": (21.3187, -157.9224),
    "NRT": (35.7647, 140.3864),
    "HND": (35.5494, 139.7798),
    "LHR": (51.4700, -0.4543),
    "CDG": (49.0097, 2.5479),
    "FCO": (41.8003, 12.2389),
    "AMS": (52.3105, 4.7683),
    "FRA": (50.0379, 8.5622),
    "BCN": (41.2974, 2.0833),
    "MAD": (40.4983, -3.5676),
    "LIS": (38.7742, -9.1342),
    "EZE": (-34.8222, -58.5358),
    "SCL": (-33.3930, -70.7858),
    "MEX": (19.4363, -99.0721),
    "CUN": (21.0365, -86.8771),
    "GIG": (-22.8100, -43.2506),
    "BSB": (-15.8711, -47.9186),
    "CGH": (-23.6261, -46.6564),
    "CNF": (-19.6244, -43.9719),
    "SSA": (-12.9086, -38.3225),
    "REC": (-8.1264, -34.9231),
    "POA": (-29.9944, -51.1714),
    "CWB": (-25.5285, -49.1758),
    "VCP": (-23.0074, -47.1345),
    "ICN": (37.4602, 126.4407),
    "SIN": (1.3644, 103.9915),
    "HKG": (22.3080, 113.9185),
    "SYD": (-33.9461, 151.1772),
    "DXB": (25.2532, 55.3657),
}


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate great-circle distance between two points in miles."""
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return round(R * c)


def calc_miles(origin: str, destination: str) -> int | None:
    """Calculate miles between two airport codes."""
    o = AIRPORTS.get(origin.upper())
    d = AIRPORTS.get(destination.upper())
    if not o or not d:
        return None
    return haversine_miles(o[0], o[1], d[0], d[1])


# Pattern: "Flight AA 1746 departing SFO at 8:02am, landing MIA at 4:28pm"
FLIGHT_PATTERN = re.compile(
    r"Flight\s+(\w+)\s+(\w+)\s+departing\s+(\w{3})\s+.*?landing\s+(\w{3})",
    re.IGNORECASE,
)


def parse_flight_event(title: str, event_date: str) -> dict | None:
    """Parse a flight event title into structured data."""
    m = FLIGHT_PATTERN.search(title)
    if not m:
        return None

    airline_code = m.group(1)
    flight_num = m.group(2)
    origin = m.group(3).upper()
    destination = m.group(4).upper()

    # Extract reservation number if present
    res_match = re.search(r"Reservation\s*#?\s*(\w+)", title, re.IGNORECASE)
    reservation = res_match.group(1) if res_match else None

    miles = calc_miles(origin, destination)

    # Map airline codes to names
    airlines = {
        "AA": "American Airlines",
        "UA": "United Airlines",
        "DL": "Delta Air Lines",
        "WN": "Southwest Airlines",
        "B6": "JetBlue",
        "AS": "Alaska Airlines",
        "NK": "Spirit Airlines",
        "F9": "Frontier Airlines",
        "LA": "LATAM Airlines",
        "G3": "Gol Airlines",
        "AD": "Azul Airlines",
    }
    airline = airlines.get(airline_code.upper(), airline_code)

    return {
        "flight_date": event_date,
        "origin_iata": origin,
        "destination_iata": destination,
        "airline": airline,
        "flight_number": f"{airline_code} {flight_num}",
        "miles": miles,
        "reservation": reservation,
    }


def group_flights_into_trips(flights: list[dict], home_airport: str = "SFO") -> list[dict]:
    """Group flights into trips based on departure from and return to home airport."""
    if not flights:
        return []

    trips = []
    current_trip_flights = []
    trip_counter = 0

    for flight in sorted(flights, key=lambda f: f["flight_date"]):
        current_trip_flights.append(flight)

        # Trip ends when we land back at home
        if flight["destination_iata"] == home_airport and len(current_trip_flights) > 1:
            trip_counter += 1
            dep_date = current_trip_flights[0]["flight_date"]
            ret_date = flight["flight_date"]
            dep = date.fromisoformat(dep_date)
            ret = date.fromisoformat(ret_date)

            # Find the furthest destination (not home, not layover hub)
            destinations = []
            for f in current_trip_flights:
                if f["destination_iata"] != home_airport:
                    destinations.append(f["destination_iata"])

            # The "main" destination is the one that's not a common US hub used for connections
            us_hubs = {"MIA", "DFW", "ORD", "ATL", "IAH", "CLT", "DEN", "PHX", "JFK", "EWR", "LAX"}
            main_dest = None
            for d in destinations:
                if d not in us_hubs:
                    main_dest = d
                    break
            if not main_dest and destinations:
                main_dest = destinations[-1]  # fallback: last non-home stop

            trip_id = f"{dep.year}-{trip_counter:03d}"
            total_miles = sum(f["miles"] or 0 for f in current_trip_flights)

            trips.append({
                "trip_id": trip_id,
                "departure_date": dep_date,
                "return_date": ret_date,
                "destination_city": main_dest or "",
                "destination_country": "",
                "purpose": "work",
                "duration_days": (ret - dep).days,
                "total_miles": total_miles,
                "flight_count": len(current_trip_flights),
            })

            # Assign trip_id to flights
            for f in current_trip_flights:
                f["trip_id"] = trip_id

            current_trip_flights = []

    # Handle open trip (haven't returned home yet)
    if current_trip_flights:
        trip_counter += 1
        dep_date = current_trip_flights[0]["flight_date"]
        dep = date.fromisoformat(dep_date)
        trip_id = f"{dep.year}-{trip_counter:03d}"
        destinations = [f["destination_iata"] for f in current_trip_flights if f["destination_iata"] != home_airport]

        trips.append({
            "trip_id": trip_id,
            "departure_date": dep_date,
            "return_date": "",
            "destination_city": destinations[-1] if destinations else "",
            "destination_country": "",
            "purpose": "work",
            "duration_days": (date.today() - dep).days,
            "total_miles": sum(f["miles"] or 0 for f in current_trip_flights),
            "flight_count": len(current_trip_flights),
        })
        for f in current_trip_flights:
            f["trip_id"] = trip_id

    return trips


# Map airport codes to cities/countries for nicer output
AIRPORT_CITIES = {
    "SFO": ("San Francisco", "USA"),
    "MIA": ("Miami", "USA"),
    "GRU": ("São Paulo", "Brazil"),
    "CGH": ("São Paulo", "Brazil"),
    "VCP": ("Campinas", "Brazil"),
    "GIG": ("Rio de Janeiro", "Brazil"),
    "BSB": ("Brasília", "Brazil"),
    "CNF": ("Belo Horizonte", "Brazil"),
    "JFK": ("New York", "USA"),
    "LAX": ("Los Angeles", "USA"),
    "ORD": ("Chicago", "USA"),
    "DFW": ("Dallas", "USA"),
    "ATL": ("Atlanta", "USA"),
    "DEN": ("Denver", "USA"),
    "SEA": ("Seattle", "USA"),
    "BOS": ("Boston", "USA"),
    "NRT": ("Tokyo", "Japan"),
    "HND": ("Tokyo", "Japan"),
    "LHR": ("London", "UK"),
    "CDG": ("Paris", "France"),
    "FCO": ("Rome", "Italy"),
    "AMS": ("Amsterdam", "Netherlands"),
    "BCN": ("Barcelona", "Spain"),
    "LIS": ("Lisbon", "Portugal"),
    "MEX": ("Mexico City", "Mexico"),
    "CUN": ("Cancún", "Mexico"),
    "EZE": ("Buenos Aires", "Argentina"),
    "SCL": ("Santiago", "Chile"),
    "ICN": ("Seoul", "South Korea"),
    "SIN": ("Singapore", "Singapore"),
    "HKG": ("Hong Kong", "China"),
    "SYD": ("Sydney", "Australia"),
    "DXB": ("Dubai", "UAE"),
}


def extract_travel_from_events(events_csv_url: str) -> None:
    """Main entry point: download events, parse flights, write trips + flights CSVs."""
    resp = httpx.get(events_csv_url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))

    if df.empty or "title" not in df.columns:
        print("[travel] No events data found")
        return

    # Parse all flight events
    flights = []
    for _, row in df.iterrows():
        title = str(row.get("title", ""))
        event_date = str(row.get("date", ""))
        parsed = parse_flight_event(title, event_date)
        if parsed:
            flights.append(parsed)

    # Deduplicate: same flight appears on multiple days for overnights.
    # Use flight_number + reservation as key, keep earliest date (departure day).
    seen = {}
    for f in flights:
        key = (f["flight_number"], f["reservation"] or "", f["origin_iata"], f["destination_iata"])
        if key not in seen or f["flight_date"] < seen[key]["flight_date"]:
            seen[key] = f
    unique_flights = sorted(seen.values(), key=lambda f: f["flight_date"])

    if not unique_flights:
        print("[travel] No flights found in calendar events")
        return

    print(f"[travel] Found {len(unique_flights)} flights")

    # Group into trips
    trips = group_flights_into_trips(unique_flights)
    print(f"[travel] Grouped into {len(trips)} trips")

    # Enrich trips with city/country names
    for trip in trips:
        code = trip["destination_city"]
        if code in AIRPORT_CITIES:
            city, country = AIRPORT_CITIES[code]
            trip["destination_city"] = city
            trip["destination_country"] = country

    # Write flights CSV
    flights_dir = RAW_DIR / "travel"
    flights_dir.mkdir(parents=True, exist_ok=True)

    flights_df = pd.DataFrame(unique_flights)
    flights_cols = ["flight_date", "trip_id", "origin_iata", "destination_iata",
                    "airline", "flight_number", "miles", "reservation"]
    flights_df = flights_df[[c for c in flights_cols if c in flights_df.columns]]
    flights_path = flights_dir / "flights.csv"
    flights_df.to_csv(flights_path, index=False)
    print(f"[travel] Wrote {len(flights_df)} flights -> {flights_path}")

    # Write trips CSV
    trips_df = pd.DataFrame(trips)
    trips_cols = ["trip_id", "departure_date", "return_date", "destination_city",
                  "destination_country", "purpose", "duration_days", "total_miles", "flight_count"]
    trips_df = trips_df[[c for c in trips_cols if c in trips_df.columns]]
    trips_path = flights_dir / "trips.csv"
    trips_df.to_csv(trips_path, index=False)
    print(f"[travel] Wrote {len(trips_df)} trips -> {trips_path}")

    # Print summary
    total_miles = sum(f.get("miles", 0) or 0 for f in unique_flights)
    total_days = sum(t.get("duration_days", 0) or 0 for t in trips)
    destinations = set(t["destination_city"] for t in trips if t["destination_city"])
    print(f"\n  Total miles flown: {total_miles:,}")
    print(f"  Days traveling: {total_days}")
    print(f"  Destinations: {', '.join(sorted(destinations))}")
