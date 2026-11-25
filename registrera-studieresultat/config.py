"""Gemensam konfiguration för alla tjänster i prototypen.

Allt kan skrivas över med miljövariabler, t.ex. LTU_API_KEY eller PORT_GUI.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Här läggs SQLite-databaserna (en per "system"). Mappen skapas automatiskt.
DATA_DIR = Path(os.environ.get("LTU_DATA_DIR", BASE_DIR / "data"))

HOST = os.environ.get("LTU_HOST", "127.0.0.1")

PORTS = {
    "gui": int(os.environ.get("PORT_GUI", 5000)),         # Resultat Canvas GUI
    "epok": int(os.environ.get("PORT_EPOK", 5001)),       # Epok (kurs- och moduldata)
    "studentits": int(os.environ.get("PORT_STUDENTITS", 5002)),  # StudentITS (identiteter)
    "ladok": int(os.environ.get("PORT_LADOK", 5003)),     # Ladok (resultatregistrering)
    "canvas": int(os.environ.get("PORT_CANVAS", 5004)),   # Canvas (simulerad, omdömen)
}

# Delad hemlighet för system-till-system-anrop (motsvarar API-gatewayen i uppgift 2).
API_KEY = os.environ.get("LTU_API_KEY", "ltu-dev-nyckel")


def url(tjanst: str) -> str:
    """Bas-URL till en av tjänsterna, t.ex. url('epok')."""
    return f"http://{HOST}:{PORTS[tjanst]}"
