from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from external_api import get_temperature
from config import WEATHER_API_KEY

WATER_PER_KG = 30
WATER_PER_ACTIVITY = 500
WATER_PER_WORKOUT = 200
WATER_HOT_WEATHER = 500

WORKOUT_CALORIES = {
    "run": 10,
    "walk": 5,
    "jump": 8,
    "tennis": 14,
    "football": 12,
}

@dataclass
class DailyStats:
    date: str
    logged_water: float = 0
    logged_calories: float = 0
    burned_calories: float = 0
    water_goal: float = 0
    calorie_goal: float = 0
    temperature: float = 0
    food_log: List[Dict] = field(default_factory=list)
    workout_log: List[Dict] = field(default_factory=list)


@dataclass
class UserProfile:
    user_id: int
    weight: float = 0
    height: float = 0
    age: int = 0
    activity_minutes: int = 0
    city: str = ""
    daily_stats: Dict[str, DailyStats] = field(default_factory=dict)

    async def get_current_stats(self) -> DailyStats:
        today = datetime.now().date().isoformat()
        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(date=today)

            temp = await get_temperature(self.city, WEATHER_API_KEY)
            if temp is not None:
                await self.update_daily_goals(temp)
            else:
                stats = self.daily_stats[today]
                stats.water_goal = self.calculate_water_goal(20)
                stats.calorie_goal = self.calculate_calorie_goal()
                stats.temperature = 20

        return self.daily_stats[today]

    def calculate_water_goal(self, temperature: float) -> float:
        base = self.weight * WATER_PER_KG
        activity = (self.activity_minutes // 30) * WATER_PER_ACTIVITY
        temp_addition = WATER_HOT_WEATHER if temperature > 25 else 0
        return base + activity + temp_addition

    def calculate_calorie_goal(self) -> float:
        bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        activity_calories = self.activity_minutes * 4
        return bmr + activity_calories

    async def update_daily_goals(self, temperature: float):
        stats = await self.get_current_stats()
        stats.water_goal = self.calculate_water_goal(temperature)
        stats.calorie_goal = self.calculate_calorie_goal()
        stats.temperature = temperature
