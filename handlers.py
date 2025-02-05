import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, BaseMiddleware
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, WEATHER_API_KEY
from logger import logger
from external_api import get_temperature, get_food_info
from models import *
from states import ProfileSetup, FoodLogging, WaterLogging, WorkoutLogging, HistoryPeriod, users

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Gomardzhoba! I'm fitness bot and I'll help you track your fitness progress.\n"
        "Use the following commands:\n\n"
        "/set_profile - set up profile\n"
        "/log_water <ml> - log water consumption\n"
        "/log_food <food> - log food consumption\n"
        "/log_workout <type> - log workout\n"
        "/check_progress - check progress\n"
        "/help - commands list\n"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "/set_profile - set up profile\n"
        "/log_water <ml> - log water consumption\n"
        "/log_food <food> - log food consumption\n"
        "/log_workout <type> - log workout\n"
        "/check_progress - check progress\n"
        "/help - commands list\n"
    )


@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileSetup.weight)
    await message.answer("Log your weight (kg):")


@router.message(ProfileSetup.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(weight=weight)
        await state.set_state(ProfileSetup.height)
        await message.answer("Log your height (cm):")
    except ValueError:
        await message.answer("Submit a number. Try once more")


@router.message(ProfileSetup.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        await state.update_data(height=height)
        await state.set_state(ProfileSetup.age)
        await message.answer("Log your age:")
    except ValueError:
        await message.answer("Submit a number. Try once more")


@router.message(ProfileSetup.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await state.set_state(ProfileSetup.activity)
        await message.answer("How many free minutes for activity do you have per day?")
    except ValueError:
        await message.answer("Submit a whole number. Try once more")


@router.message(ProfileSetup.activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        await state.update_data(activity=activity)
        await state.set_state(ProfileSetup.city)
        await message.answer("Which city are you located in?")
    except ValueError:
        await message.answer("Submit a whole number. Try once more")


@router.message(ProfileSetup.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text
    user_data = await state.get_data()
    user_id = message.from_user.id

    profile = UserProfile(
        user_id=user_id,
        weight=user_data['weight'],
        height=user_data['height'],
        age=user_data['age'],
        activity_minutes=user_data['activity'],
        city=city
    )

    try:
        temp = await get_temperature(city, WEATHER_API_KEY)
        if temp is None:
            raise ValueError("Failed to get temperature")

        users[user_id] = profile
        stats = await profile.get_current_stats()

        await state.clear()
        logger.info("Profile set up for user {}", user_id)
        await message.answer(
            "Profile setup finished!\n"
            f"Your water goal: {stats.water_goal:.0f} ml\n"
            f"Your calories goal: {stats.calorie_goal:.0f} kcal\n"
        )
    except Exception as e:
        logger.error("Error setting up profile: {}", e)
        await message.answer(
            "Unable to retrieve weather information.\n"
            "Check validity of input city name\n"
        )


@router.message(Command("log_water"))
async def cmd_log_water(message: Message, command: CommandObject, state: FSMContext):
    if not command.args:
        await state.set_state(WaterLogging.waiting_for_water)
        await message.answer("Please provide the quantity of water drunk in ml:")
        return

    user_id = message.from_user.id
    stats = await users[user_id].get_current_stats()

    water_text = command.args
    
    try:
        water_amount = float(water_text)
        stats.logged_water += water_amount
        remaining = stats.water_goal - stats.logged_water
        await message.answer(
            f"Logged: {water_amount} ml of water\n"
            f"Remaining to drink: {max(0, remaining)} ml"
        )
    except ValueError:
        await message.answer("Please enter a valid number.")


@router.message(WaterLogging.waiting_for_water)
async def process_water_logging(message: Message, state: FSMContext):
    await state.clear()
    await cmd_log_water(message, CommandObject(prefix="/", command="log_water", args=message.text), state)


@router.message(Command("log_food"))
async def cmd_log_food(message: Message, command: CommandObject, state: FSMContext):
    if not command.args:
        await state.set_state(FoodLogging.waiting_for_food_name)
        await message.answer(
            "Submit the food name (in English)."
        )
        return

    food_info = await get_food_info(command.args)

    if not food_info:
        logger.error("Food not found: {}", command.args)
        await message.answer(
            "Sorry, couldn't find information about this food.\n"
            "Try another food or check the spelling."
        )
        return
    if food_info.get("error"):
        error_message = f"Error getting food information: {food_info['name']}\n"
        error_message += "Try another food or check the spelling."
        if food_info.get("suggest"):
            error_message += f"\n**Note**: {food_info['suggest']}"
        await message.answer(error_message)
        return
    try:
        await state.update_data(
            food_name=food_info["name"],
            calories_per_100=float(food_info["calories"])
        )
        await state.set_state(FoodLogging.waiting_for_weight)
        await message.answer(
            f"Logged: {food_info['name']}\n"
            f"Calories: {food_info['calories']:.1f} kcal/100g\n"
            "How many grams did you eat?"
        )
    except Exception as e:
        logger.error("Error processing food information: {}", e)
        await message.answer(
            "An error occurred while processing food information.\n"
            "Please try another food."
        )


@router.message(FoodLogging.waiting_for_food_name)
async def process_food_name(message: Message, state: FSMContext):
    await state.clear()
    await cmd_log_food(message, CommandObject(prefix="/", command="log_food", args=message.text), state)


@router.message(FoodLogging.waiting_for_weight)
async def process_food_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        food_data = await state.get_data()
        calories = food_data['calories_per_100'] * weight / 100

        user_id = message.from_user.id
        stats = await users[user_id].get_current_stats()
        stats.logged_calories += calories
        stats.food_log.append({
            "name": food_data['food_name'],
            "weight": weight,
            "calories": calories,
            "timestamp": datetime.now().isoformat()
        })

        await state.clear()
        await message.answer(
            f"Logged: {food_data['food_name']}\n"
            f"- Weight: {weight} g\n"
            f"- Calories: {calories:.1f} kcal"
        )
    except ValueError:
        await message.answer("Please enter the weight in grams as a number.")


async def validate_workout_type(message, workout_type):
    if not workout_type or workout_type not in WORKOUT_CALORIES:
        await message.answer(
            "Unknown workout type.\n"
            "Available types: " + ", ".join(WORKOUT_CALORIES.keys())
        )
        return False
    return True


@router.message(WorkoutLogging.waiting_for_workout_type)
async def process_workout_type(message: Message, state: FSMContext):
    if not await validate_workout_type(message, message.text):
        return

    await state.update_data(workout_type=message.text)
    await state.set_state(WorkoutLogging.waiting_for_workout_duration)
    await message.answer("How many minutes did you workout?")


@router.message(WorkoutLogging.waiting_for_workout_duration)
async def process_workout_duration(message: Message, state: FSMContext):
    try:
        workout_duration = int(message.text)
    except ValueError:
        await message.answer("Please enter the workout duration as a number in minutes.")
        return

    await state.update_data(workout_duration=workout_duration)
    await state.set_state(WorkoutLogging.commit_workout)
    await cmd_log_workout(message, CommandObject(prefix="/", command="log_workout"), state)


@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message, command: CommandObject, state: FSMContext):
    state_data = await state.get_data()

    current_state = await state.get_state()
    if current_state != WorkoutLogging.commit_workout:
        if state_data.get('workout_type', None) is None:
            if command.args:
                if await validate_workout_type(message, command.args):
                    await state.update_data(workout_type=command.args)
                    await state.set_state(WorkoutLogging.waiting_for_workout_duration)
                    await message.answer("How many minutes did you workout?")
            else:
                await state.set_state(WorkoutLogging.waiting_for_workout_type)
                await message.answer(
                    "Please specify the workout type.\n"
                    "Available types: " + ", ".join(WORKOUT_CALORIES.keys())
                )
            return
        if state_data.get('workout_duration', None) is None:
            await state.set_state(WorkoutLogging.waiting_for_workout_duration)
            await message.answer("How many minutes did you workout?")
            return
        return

    user_id = message.from_user.id
    stats = await users[user_id].get_current_stats()
    workout_type = state_data['workout_type']
    workout_duration = state_data['workout_duration']

    try:
        calories_burned = WORKOUT_CALORIES[workout_type] * workout_duration
        water_needed = (workout_duration // 30) * WATER_PER_WORKOUT

        stats.burned_calories += calories_burned
        stats.workout_log.append({
            "type": workout_type,
            "duration": workout_duration,
            "calories": calories_burned,
            "timestamp": datetime.now().isoformat()
        })
        await state.clear()
        await message.answer(
            f"Logged:{workout_type.capitalize()} {workout_duration} minutes\n"
            f"- Calories burned: {calories_burned} kcal\n"
            f"  Recommended water intake: {water_needed} ml of water"
        )
    except ValueError:
        await message.answer("Please enter the workout duration in minutes as a number.")
    except Exception as e:
        await message.answer("An error occurred while logging the workout: %s", e)


@router.message(Command("check_progress"))
async def cmd_check_progress(message: Message):
    user_id = message.from_user.id
    user = users[user_id]
    stats = await user.get_current_stats()

    temp = await get_temperature(user.city, WEATHER_API_KEY)
    if temp is not None:
        await user.update_daily_goals(temp)

        if abs(temp - stats.temperature) > 5:
            temp_diff = "increased" if temp > stats.temperature else "decreased"
            await message.answer(
                f"Temperature {temp_diff}!\n"
                f"New recommendation for water intake: {stats.water_goal} ml"
            )

    await message.answer(
        "Today progress:\n"
        f"Water consumption:\n"
        f"- Drunk: {stats.logged_water} ml out of {stats.water_goal} ml.\n"
        f"- Remaining: {max(0, stats.water_goal - stats.logged_water)} ml.\n\n"
        f"Calories consumption:\n"
        f"- Consumed: {stats.logged_calories} kcal out of BMR = {stats.calorie_goal} kcal.\n"
        f"- Burned: {stats.burned_calories} kcal.\n"
        f"- Balance (consumed - BMR - burned): "
        f"{stats.logged_calories - stats.calorie_goal - stats.burned_calories} kcal.\n\n"
        f"Good job! Keep going!:\n"
    )
