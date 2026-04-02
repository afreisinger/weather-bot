import logging
import sys
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style, init

# Inicializa colorama
init(autoreset=True)

# ───────── Formateador coloreado para consola ─────────
class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, "")
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

# ───────── Rutas y archivos ─────────
LOG_FILE = "/var/log/weather/weather.log"

# ───────── Handler de consola ─────────
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColorFormatter(
    "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
))

# ───────── Handler de archivo rotativo ─────────
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3,
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
))

# ───────── Configuración global del logger ─────────
logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler],)
logger = logging.getLogger(__name__)