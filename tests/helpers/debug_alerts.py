import asyncio
from weather.skills.weather.skill import WeatherSkill

async def main():
    skill = WeatherSkill()
    result = await skill.alerts("Buenos Aires")
    print(result)

asyncio.run(main())