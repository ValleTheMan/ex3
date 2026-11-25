"""Epok - utbildningsdatabasen. Tillhandahåller kurs- och moduldata.

Webbtjänsten get_Modul (enligt uppgiften) motsvaras av:
    GET /api/epok/kurser/{kurskod}/moduler
Den returnerar kursens AKTIVA moduler. Övriga endpoints (POST/PUT/DELETE) är
administrativa och visar att tjänsten följer REST-principerna fullt ut.
"""
import re

from flask import jsonify, request

import config
from common.service import fel, get_db, hamta_json, skapa_tjanst

app = skapa_tjanst("Epok", __name__, "epok.db")

MODULKOD = re.compile(r"^\d{4}$")


def _modul_json(rad):
    return {
        "modul": rad["modul"],
        "benamning": rad["benamning"],
        "hp": rad["hp"],
        "aktiv": bool(rad["aktiv"]),
    }


def _hamta_kurs(kurskod):
    return get_db().execute(
        "SELECT kurskod, namn FROM kurs WHERE kurskod = ?", (kurskod.strip().upper(),)
    ).fetchone()


def _validera_falt(data, kravs_alla):
    """Validerar modulens fält. Returnerar (falt, felmeddelande)."""
    falt = {}
    if kravs_alla or "benamning" in data:
        v = data.get("benamning")
        if not isinstance(v, str) or not v.strip():
            return None, "benamning måste vara en icke-tom text."
        falt["benamning"] = v.strip()
    if kravs_alla or "hp" in data:
        v = data.get("hp")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
            return None, "hp måste vara ett positivt tal."
        falt["hp"] = float(v)
    if "aktiv" in data:
        if not isinstance(data["aktiv"], bool):
            return None, "aktiv måste vara true eller false."
        falt["aktiv"] = 1 if data["aktiv"] else 0
    return falt, None


@app.get("/api/epok/kurser")
def lista_kurser():
    rader = get_db().execute("SELECT kurskod, namn FROM kurs ORDER BY kurskod").fetchall()
    return jsonify(kurser=[{"kurskod": r["kurskod"], "namn": r["namn"]} for r in rader])


@app.get("/api/epok/kurser/<kurskod>/moduler")
def get_modul(kurskod):
    """get_Modul: tar emot en kurskod och returnerar kursens aktiva moduler."""
    kurs = _hamta_kurs(kurskod)
    if kurs is None:
        return fel(f"Kursen {kurskod.upper()} finns inte i Epok.", 404)
    rader = get_db().execute(
        "SELECT modul, benamning, hp, aktiv FROM modul "
        "WHERE kurskod = ? AND aktiv = 1 ORDER BY modul",
        (kurs["kurskod"],),
    ).fetchall()
    return jsonify(
        kurskod=kurs["kurskod"],
        kursnamn=kurs["namn"],
        moduler=[_modul_json(r) for r in rader],
    )


@app.post("/api/epok/kurser/<kurskod>/moduler")
def skapa_modul(kurskod):
    kurs = _hamta_kurs(kurskod)
    if kurs is None:
        return fel(f"Kursen {kurskod.upper()} finns inte i Epok.", 404)
    data = hamta_json()
    if data is None:
        return fel("Anropet måste innehålla ett JSON-objekt.", 400)
    modul = data.get("modul")
    if not isinstance(modul, str) or not MODULKOD.match(modul):
        return fel("modul måste vara en fyrsiffrig kod, t.ex. '0005'.", 400)
    falt, fel_text = _validera_falt(data, kravs_alla=True)
    if fel_text:
        return fel(fel_text, 400)
    db = get_db()
    if db.execute(
        "SELECT 1 FROM modul WHERE kurskod = ? AND modul = ?", (kurs["kurskod"], modul)
    ).fetchone():
        return fel(f"Modul {modul} finns redan i kursen {kurs['kurskod']}.", 409)
    db.execute(
        "INSERT INTO modul (kurskod, modul, benamning, hp, aktiv) VALUES (?, ?, ?, ?, ?)",
        (kurs["kurskod"], modul, falt["benamning"], falt["hp"], falt.get("aktiv", 1)),
    )
    db.commit()
    rad = db.execute(
        "SELECT modul, benamning, hp, aktiv FROM modul WHERE kurskod = ? AND modul = ?",
        (kurs["kurskod"], modul),
    ).fetchone()
    return jsonify(_modul_json(rad)), 201


@app.put("/api/epok/kurser/<kurskod>/moduler/<modul>")
def uppdatera_modul(kurskod, modul):
    kurs = _hamta_kurs(kurskod)
    if kurs is None:
        return fel(f"Kursen {kurskod.upper()} finns inte i Epok.", 404)
    data = hamta_json()
    if data is None:
        return fel("Anropet måste innehålla ett JSON-objekt.", 400)
    falt, fel_text = _validera_falt(data, kravs_alla=False)
    if fel_text:
        return fel(fel_text, 400)
    if not falt:
        return fel("Ange minst ett av fälten benamning, hp eller aktiv.", 400)
    db = get_db()
    # Kolumnnamnen kommer från _validera_falt (fast lista), aldrig direkt från användaren.
    set_sats = ", ".join(f"{kolumn} = ?" for kolumn in falt)
    resultat = db.execute(
        f"UPDATE modul SET {set_sats} WHERE kurskod = ? AND modul = ?",
        (*falt.values(), kurs["kurskod"], modul),
    )
    db.commit()
    if resultat.rowcount == 0:
        return fel(f"Modul {modul} finns inte i kursen {kurs['kurskod']}.", 404)
    rad = db.execute(
        "SELECT modul, benamning, hp, aktiv FROM modul WHERE kurskod = ? AND modul = ?",
        (kurs["kurskod"], modul),
    ).fetchone()
    return jsonify(_modul_json(rad))


@app.delete("/api/epok/kurser/<kurskod>/moduler/<modul>")
def ta_bort_modul(kurskod, modul):
    db = get_db()
    resultat = db.execute(
        "DELETE FROM modul WHERE kurskod = ? AND modul = ?", (kurskod.strip().upper(), modul)
    )
    db.commit()
    if resultat.rowcount == 0:
        return fel(f"Modul {modul} finns inte i kursen {kurskod.upper()}.", 404)
    return "", 204


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORTS["epok"])
