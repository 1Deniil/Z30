# 🧠 Dual Bot System: Minecraft & Discord

This project is a dual bot system consisting of:
- A **Minecraft bot** for interacting with in-game events, statistics, and chat.
- A **Discord bot** for handling commands, events, and relaying data from Minecraft.

---

## 📁 Project Structure

```bash
project/
├── config/                  # Configuration files
│   ├── settings.py          # General configuration
│   └── credentials.py       # Sensitive data (tokens, etc.)
├── shared/                  # Shared utilities
│   ├── logging_utils.py     # Logging setup
│   ├── file_utils.py        # File operations
│   ├── timing_utils.py      # Performance measurement
│   └── shortcuts.py         # Command shortcuts manager
├── minecraft_bot/           # Minecraft bot logic
│   ├── client.py            # Minecraft client logic
│   ├── commands.py          # In-game command handling
│   ├── stats.py             # Web scraping (stats)
│   ├── relay.py             # Relays messages to Discord
│   └── utils.py             # Specific helper functions
├── discord_bot/             # Discord bot logic
│   ├── bot.py               # Discord bot setup
│   ├── commands.py          # Slash commands
│   ├── events.py            # Event listeners
│   └── utils.py             # Specific helper functions
├── data/                    # Persistent data
│   ├── shortcuts.json       # Command shortcuts
│   └── user_shortcuts.json  # User-defined aliases
├── logs/                    # Logging output
│   ├── latest.log           # Minecraft logs
│   └── bot.log              # Discord bot logs
├── z30.py                  # Minecraft bot entry point
├── z30bot.py          # Discord bot entry point
└── requirements.txt         # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Java (if required for Minecraft integration)
- Dependencies listed in `requirements.txt`

### Installation

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Setup

1. Create your own `config/credentials.py` file based on the template:
   ```python
   DISCORD_TOKEN = "your_discord_token_here"
   MINECRAFT_EMAIL = "your_email"
   MINECRAFT_PASSWORD = "your_password"
   ```
2. Edit `config/settings.py` to customize general bot behavior.

---

## 🧠 Usage

### Run Minecraft Bot
```bash
python main.py
```

### Run Discord Bot
```bash
python discord_main.py
```

---

## ✨ Features

- Modular and scalable bot architecture.
- Real-time relay between Minecraft and Discord.
- Web scraping for live Minecraft statistics.
- User-customizable shortcuts and aliases.
- Performance monitoring and logging utilities.

---

## 📌 Notes

- Make sure to keep your credentials safe.
- Logs are automatically written to the `logs/` folder.
- Data like shortcuts are stored in `data/`.

---

## 📜 License

MIT License — feel free to use and modify for your projects.
