"""Pydantic models for data validation."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class OuraSleep(BaseModel):
    date: date
    score: Optional[int] = None
    total_sleep_min: Optional[int] = None
    deep_min: Optional[int] = None
    rem_min: Optional[int] = None
    light_min: Optional[int] = None
    awake_min: Optional[int] = None
    efficiency: Optional[int] = None
    hr_lowest: Optional[int] = None
    hr_average: Optional[int] = None
    hrv_average: Optional[int] = None
    breath_average: Optional[float] = None


class OuraReadiness(BaseModel):
    date: date
    score: Optional[int] = None
    temperature_deviation: Optional[float] = None
    hrv_balance: Optional[int] = None
    recovery_index: Optional[int] = None
    resting_heart_rate: Optional[int] = None


class OuraActivity(BaseModel):
    date: date
    score: Optional[int] = None
    active_calories: Optional[int] = None
    steps: Optional[int] = None
    equivalent_walking_distance: Optional[int] = None


class AppleHealthWorkout(BaseModel):
    date: date
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    type: Optional[str] = None
    duration_min: Optional[int] = None
    active_calories: Optional[int] = None
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None


class AppleHealthSteps(BaseModel):
    date: date
    steps: Optional[int] = None


class AppleHealthSleep(BaseModel):
    date: date
    asleep_hr: Optional[float] = None
    in_bed_hr: Optional[float] = None
    deep_hr: Optional[float] = None
    rem_hr: Optional[float] = None
    core_hr: Optional[float] = None
    source: Optional[str] = None


class SaunaSession(BaseModel):
    date: date
    start_time: Optional[datetime] = None
    type: str = Field(pattern=r"^(sauna|cold_plunge|both)$")
    duration_min: Optional[int] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None


class WorkHours(BaseModel):
    date: date
    first_event_time: Optional[str] = None
    last_event_time: Optional[str] = None
    total_work_hr: Optional[float] = None
    meeting_count: Optional[int] = None
    meeting_hr: Optional[float] = None
    focus_hr: Optional[float] = None


class TravelTrip(BaseModel):
    trip_id: str
    departure_date: date
    return_date: date
    destination_city: str
    destination_country: str
    purpose: Optional[str] = None
    duration_days: Optional[int] = None


class TravelFlight(BaseModel):
    flight_date: date
    trip_id: Optional[str] = None
    origin_iata: str
    destination_iata: str
    airline: Optional[str] = None
    miles: Optional[int] = None
    duration_hr: Optional[float] = None


class WeatherDaily(BaseModel):
    date: date
    location: Optional[str] = None
    high_f: Optional[float] = None
    low_f: Optional[float] = None
    condition: Optional[str] = None
    humidity: Optional[int] = None


class MoodEntry(BaseModel):
    date: date
    time: Optional[str] = None
    mood: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    notes: Optional[str] = None
