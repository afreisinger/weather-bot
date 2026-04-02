# 🌤 Weather Bot

A Telegram bot that provides real-time weather information powered by the **OpenWeather OneCall 3.0 API**. It supports current conditions, multi-day forecasts, hourly forecasts, and weather alerts — all accessible via Telegram commands or a CLI tool.

The project is built with Python 3.12, aiogram 3.x, and can be easily integrated with OpenClaw for agent automation or LLM pipelines

---

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
  - [Locally](#locally)
  - [With Docker](#with-docker)
  - [With Docker Compose](#with-docker-compose)
- [CLI Usage](#cli-usage)
- [Telegram Commands](#telegram-commands)
- [Running Tests](#running-tests)
- [Architecture Overview](#architecture-overview)

---

## ✨ Features

- 🌡 **Current weather** — temperature, humidity, wind speed, and conditions.
- 📅 **Multi-day forecast** — up to 8 days ahead.
- ⏱ **Hourly forecast** — up to 48 hours ahead.
- 🚨 **Weather alerts** — active alerts for any city.
- ⚡ **In-memory caching** — 5-minute TTL to reduce API calls.
- 🔄 **Auto-retry** — exponential backoff on transient network errors.
- 🐳 **Docker-ready** — multi-stage Dockerfile with a non-root user.
- 🖥 **CLI interface** — query weather directly from the terminal.

---

## 📁 Project Structure

```
weather-bot/
├── cli/
│   └── weather_cli.py          # CLI entrypoint
├── config/
│   └── config.yaml             # App configuration (city, units, defaults)
├── logs/                       # Log output directory
├── tests/
│   ├── test_weather.py         # Unit + integration tests (fully mocked)
│   └── helpers/
│       └── telegram_sender.py  # Test helpers
├── weather/
│   ├── bot/
│   │   ├── main.py             # Bot entrypoint (aiogram)
│   │   └── handlers.py         # Telegram command handlers
│   ├── core/
│   │   ├── config.py           # Settings loader (YAML + env vars)
│   │   └── logging.py          # Logger setup
│   └── skills/
│       └── weather/
│           ├── client.py       # Async OpenWeather API client
│           ├── formatters.py   # Response formatters
│           ├── schema.py       # Tool-call schema handler
│           └── skill.py        # WeatherSkill core logic
├── .env.sample                 # Environment variable template
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## ✅ Requirements

- Python **3.12+**
- A **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- An **OpenWeather API Key** with access to [OneCall 3.0](https://openweathermap.org/api/one-call-3)

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/afreisinger/weather-bot.git
cd weather-bot

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Environment Variables

Copy the sample file and fill in your credentials:

```bash
cp .env.sample .env
```

| Variable               | Description                          |
|------------------------|--------------------------------------|
| `TELEGRAM_TOKEN`       | Your Telegram Bot token              |
| `OPENWEATHER_API_KEY`  | Your OpenWeather API key             |
| `CONFIG_PATH`          | *(Optional)* Custom config file path |

### `config/config.yaml`

```yaml
weather:
  default_city: "Buenos Aires"
  units: "metric"         # metric | imperial | standard
  forecast_days: 3        # Default days for /forecast (1–8)
  forecast_hours: 12      # Default hours for /forecast_hourly (1–48)
```

---

## ▶️ Running the Bot

### Locally

```bash
export TELEGRAM_TOKEN=your_token
export OPENWEATHER_API_KEY=your_key

python -m weather.bot.main
```

### With Docker

```bash
# Build
docker build -t weather-bot .

# Run
docker run --env-file .env -v $(pwd)/config:/app/config weather-bot
```

### With Docker Compose

```bash
docker compose up --build
```

> The `docker-compose.yml` mounts `./config` and `./logs` as volumes and automatically restarts the container on failure.

---

## 🖥 CLI Usage

Query weather directly from your terminal without running the bot:

```bash
# Current weather
python -m cli.weather_cli current "London"

# 5-day forecast
python -m cli.weather_cli forecast "Córdoba" --days 5

# Enable debug logging
python -m cli.weather_cli -v current "Tokyo"
```

---

## 💬 Telegram Commands

| Command                          | Description                                  |
|----------------------------------|----------------------------------------------|
| `/weather`                       | Current weather for the default city         |
| `/weather <city>`                | Current weather for a specific city          |
| `/forecast`                      | 3-day forecast for the default city          |
| `/forecast <city>`               | 3-day forecast for a specific city           |
| `/forecast <city> <days>`        | Custom-day forecast (1–8 days)               |
| `/forecast_hourly`               | 12-hour forecast for the default city        |
| `/forecast_hourly <city>`        | 12-hour forecast for a specific city         |
| `/forecast_hourly <city> <hours>`| Custom hourly forecast (1–48 hours)          |
| `/alerts`                        | Active weather alerts for the default city   |
| `/alerts <city>`                 | Active weather alerts for a specific city    |
| `/help`                          | Show all available commands                  |

---

## 🧪 Running Tests

Tests are fully mocked — no real network calls or API keys are required.

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=weather --cov-report=term-missing
```

---

## 🏗 Architecture Overview

```
Telegram User
     │
     ▼
[aiogram Handlers]  ←── weather/bot/handlers.py
     │
     ▼
[WeatherSkill]      ←── weather/skills/weather/skill.py
     │
     ├──► [Geocoding API]    ─┐
     └──► [OneCall 3.0 API]  ─┤── weather/skills/weather/client.py
                              │   (retry, cache, validation)
                              ▼
                       [Formatters]  ←── weather/skills/weather/formatters.py
                              │
                              ▼
                      Formatted string response
```

- **`WeatherSkill`** is transport-agnostic — it can be used by the Telegram bot, the CLI, or any other interface.
- **`client.py`** handles all HTTP communication with in-memory caching and exponential backoff retries.
- **`config.py`** merges `config.yaml` defaults with environment variable overrides.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
