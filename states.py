from aiogram.fsm.state import State, StatesGroup

users = {}

class ProfileSetup(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()


class FoodLogging(StatesGroup):
    waiting_for_weight = State()
    waiting_for_food_name = State()


class WaterLogging(StatesGroup):
    waiting_for_water = State()


class WorkoutLogging(StatesGroup):
    waiting_for_workout_type = State()
    waiting_for_workout_duration = State()
    commit_workout = State()


class HistoryPeriod(StatesGroup):
    waiting_for_period = State()