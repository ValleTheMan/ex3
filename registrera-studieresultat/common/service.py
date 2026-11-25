"""Gemensam grund för tjänsterna.

Varje "system" (Epok, StudentITS, Ladok, Canvas) är en egen Flask-app med en egen
SQLite-databas. Den här modulen ger dem:
  * databasinitiering från schema.sql / seed.sql (data ligger alltså inte i koden),
  * kontroll av API-nyckel (header X-API-Key),
  * enhetliga JSON-felsvar.
"""
import hmac
import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException

import config

FELTEXTER = {
    400: "Anropet är felaktigt utformat.",
    404: "Resursen hittades inte.",
    405: "HTTP-metoden stöds inte för den här resursen.",
}


def fel(meddelande, status_kod, status="fel"):
    """Enhetligt JSON-felsvar: {"status": ..., "meddelande": ...}."""
    return jsonify(status=status, meddelande=meddelande), status_kod


def hamta_json():
    """JSON-kroppen som dict, eller None om den saknas eller är ogiltig."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def get_db():
    """SQLite-anslutning för pågående request (stängs automatiskt efteråt)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def _initiera_databas(db_path: Path, tjanst_dir: Path):
    """Skapar tabeller (schema.sql) och fyller en NY databas med testdata (seed.sql)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ny_databas = not db_path.exists()
    with closing(sqlite3.connect(db_path)) as conn:
        conn.executescript((tjanst_dir / "schema.sql").read_text(encoding="utf-8"))
        seed = tjanst_dir / "seed.sql"
        if ny_databas and seed.exists():
            conn.executescript(seed.read_text(encoding="utf-8"))
        conn.commit()


def skapa_tjanst(namn, import_name, db_fil=None, kraver_nyckel=True):
    """Skapar en Flask-app för ett av systemen.

    namn          visningsnamn (t.ex. "Epok")
    import_name   skickas vidare till Flask (använd __name__)
    db_fil        filnamn för SQLite-databasen, eller None om tjänsten saknar databas
    kraver_nyckel om True krävs headern X-API-Key på alla anrop utom /health
    """
    app = Flask(import_name)
    app.json.ensure_ascii = False   # låt å, ä, ö vara läsbara i JSON-svaren
    app.json.sort_keys = False
    app.config["TJANST_NAMN"] = namn

    if db_fil:
        app.config["DB_PATH"] = config.DATA_DIR / db_fil
        _initiera_databas(app.config["DB_PATH"], Path(app.root_path))

    @app.teardown_appcontext
    def stang_db(_undantag):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    if kraver_nyckel:
        @app.before_request
        def kontrollera_nyckel():
            if request.path == "/health":
                return None
            skickad = request.headers.get("X-API-Key", "").encode("utf-8")
            if not hmac.compare_digest(skickad, config.API_KEY.encode("utf-8")):
                return fel("API-nyckel saknas eller är ogiltig (header X-API-Key).", 401)
            return None

    @app.get("/health")
    def health():
        return jsonify(status="ok", tjanst=namn)

    @app.errorhandler(HTTPException)
    def hantera_http_fel(e):
        return fel(FELTEXTER.get(e.code, e.description), e.code)

    @app.errorhandler(Exception)
    def hantera_ovantat_fel(e):
        app.logger.exception("Oväntat fel")
        return fel("Internt serverfel.", 500)

    return app
