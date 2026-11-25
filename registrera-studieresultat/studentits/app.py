"""StudentITS - studentadministrativt system som kopplar användarnamn till personnummer.

Webbtjänsten get_Persnummer (enligt uppgiften) motsvaras av:
    GET /api/studentits/studenter/{anvandarnamn}/personnummer
Varje uppslag loggas i tabellen atkomstlogg (GDPR / spårbarhet).
"""
from flask import jsonify, request

import config
from common.service import fel, get_db, skapa_tjanst

app = skapa_tjanst("StudentITS", __name__, "studentits.db")


@app.get("/api/studentits/studenter/<anvandarnamn>/personnummer")
def get_persnummer(anvandarnamn):
    """get_Persnummer: tar emot ett studentanvändarnamn och returnerar personnummer."""
    anvandarnamn = anvandarnamn.strip()
    db = get_db()
    rad = db.execute(
        "SELECT anvandarnamn, personnummer FROM student WHERE anvandarnamn = ?",
        (anvandarnamn,),
    ).fetchone()
    db.execute(
        "INSERT INTO atkomstlogg (anvandarnamn, anropare, traff) VALUES (?, ?, ?)",
        (anvandarnamn, request.headers.get("X-Caller", "okänd")[:80], 1 if rad else 0),
    )
    db.commit()
    if rad is None:
        return fel(f"Ingen student med användarnamnet '{anvandarnamn}' finns i StudentITS.", 404)
    return jsonify(anvandarnamn=rad["anvandarnamn"], personnummer=rad["personnummer"])


@app.get("/api/studentits/atkomstlogg")
def atkomstlogg():
    """De senaste uppslagen (utan personnummer) - för granskning."""
    try:
        grans = min(max(int(request.args.get("limit", 50)), 1), 500)
    except ValueError:
        return fel("limit måste vara ett heltal.", 400)
    rader = get_db().execute(
        "SELECT id, tidpunkt, anvandarnamn, anropare, traff FROM atkomstlogg "
        "ORDER BY id DESC LIMIT ?",
        (grans,),
    ).fetchall()
    return jsonify(logg=[{**dict(r), "traff": bool(r["traff"])} for r in rader])


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORTS["studentits"])
