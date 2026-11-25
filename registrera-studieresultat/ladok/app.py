"""Ladok - studiedokumentationssystemet. Lagrar registrerade studieresultat.

Webbtjänsten reg_Resultat (enligt uppgiften) motsvaras av:
    POST /api/ladok/resultat
    { "personnummer": "19940613-2345", "kurskod": "D0031N",
      "modul": "0005", "datum": "2026-11-20", "betyg": "G" }

Svaret innehåller alltid ett statusmeddelande:
    "registrerad"  (HTTP 201)            resultatet har sparats
    "hinder"       (HTTP 400/409/422)    resultatet kunde inte registreras, se "meddelande"
"""
import re
import sqlite3
from datetime import date, datetime

from flask import jsonify, request

import config
from common.service import fel, get_db, hamta_json, skapa_tjanst

app = skapa_tjanst("Ladok", __name__, "ladok.db")

# Obs: vi kontrollerar bara FORMATET på personnummer, inte kontrollsiffran (Luhn),
# eftersom testdata är påhittad.
PERSONNUMMER = re.compile(r"^\d{8}-\d{4}$")
KURSKOD = re.compile(r"^[A-Z0-9]{4,10}$")
MODULKOD = re.compile(r"^\d{4}$")
OBLIGATORISKA_FALT = ("personnummer", "kurskod", "modul", "datum", "betyg")


def hinder(meddelande, status_kod):
    return fel(meddelande, status_kod, status="hinder")


def _resultat_json(rad):
    return {
        "id": rad["id"],
        "personnummer": rad["personnummer"],
        "kurskod": rad["kurskod"],
        "modul": rad["modul"],
        "betyg": rad["betyg"],
        "datum": rad["examinationsdatum"],
        "registrerad": rad["registrerad"],
    }


@app.get("/api/ladok/betygsskala")
def betygsskala():
    rader = get_db().execute("SELECT kod, beskrivning FROM betygsskala ORDER BY rowid").fetchall()
    return jsonify(betygsskala=[{"kod": r["kod"], "beskrivning": r["beskrivning"]} for r in rader])


@app.post("/api/ladok/resultat")
def reg_resultat():
    """reg_Resultat: validerar och lagrar ett studieresultat, returnerar ett statusmeddelande."""
    data = hamta_json()
    if data is None:
        return hinder("Anropet måste innehålla ett JSON-objekt.", 400)

    saknas = [
        f for f in OBLIGATORISKA_FALT
        if not isinstance(data.get(f), str) or not data[f].strip()
    ]
    if saknas:
        return hinder("Obligatoriska uppgifter saknas: " + ", ".join(saknas) + ".", 400)

    personnummer = data["personnummer"].strip()
    kurskod = data["kurskod"].strip().upper()
    modul = data["modul"].strip()
    betyg = data["betyg"].strip().upper()

    if not PERSONNUMMER.match(personnummer):
        return hinder("Personnummer måste ha formatet ÅÅÅÅMMDD-XXXX.", 422)
    if not KURSKOD.match(kurskod):
        return hinder(f"Ogiltig kurskod: '{kurskod}'.", 422)
    if not MODULKOD.match(modul):
        return hinder("Modul måste vara en fyrsiffrig kod, t.ex. 0005.", 422)

    try:
        datum = datetime.strptime(data["datum"].strip(), "%Y-%m-%d").date()
    except ValueError:
        return hinder("Datum måste ha formatet ÅÅÅÅ-MM-DD.", 422)
    if datum > date.today():
        return hinder("Examinationsdatum får inte ligga i framtiden.", 422)

    db = get_db()
    if db.execute("SELECT 1 FROM betygsskala WHERE kod = ?", (betyg,)).fetchone() is None:
        return hinder(f"Betyget '{betyg}' finns inte i betygsskalan.", 422)

    if db.execute(
        "SELECT 1 FROM kursregistrering WHERE personnummer = ? AND kurskod = ?",
        (personnummer, kurskod),
    ).fetchone() is None:
        return hinder(f"Studenten saknar registrering på kursen {kurskod}.", 422)

    befintligt = db.execute(
        "SELECT betyg, examinationsdatum FROM resultat "
        "WHERE personnummer = ? AND kurskod = ? AND modul = ?",
        (personnummer, kurskod, modul),
    ).fetchone()
    if befintligt:
        return hinder(
            f"Modul {modul} har redan ett registrerat resultat "
            f"({befintligt['betyg']}, {befintligt['examinationsdatum']}).",
            409,
        )

    try:
        cur = db.execute(
            "INSERT INTO resultat (personnummer, kurskod, modul, betyg, examinationsdatum) "
            "VALUES (?, ?, ?, ?, ?)",
            (personnummer, kurskod, modul, betyg, datum.isoformat()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return hinder(f"Modul {modul} har redan ett registrerat resultat.", 409)

    rad = db.execute("SELECT * FROM resultat WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(
        status="registrerad",
        meddelande="Resultatet har registrerats i Ladok.",
        resultat=_resultat_json(rad),
    ), 201


@app.get("/api/ladok/resultat")
def lista_resultat():
    """Hämtar registrerade resultat. Valfria filter: personnummer, kurskod, modul."""
    villkor, parametrar = [], []
    for falt in ("personnummer", "kurskod", "modul"):
        varde = request.args.get(falt, "").strip()
        if varde:
            villkor.append(f"{falt} = ?")  # kolumnnamn från fast lista ovan
            parametrar.append(varde.upper() if falt == "kurskod" else varde)
    sql = "SELECT * FROM resultat"
    if villkor:
        sql += " WHERE " + " AND ".join(villkor)
    rader = get_db().execute(sql + " ORDER BY id", parametrar).fetchall()
    return jsonify(resultat=[_resultat_json(r) for r in rader])


@app.get("/api/ladok/resultat/<int:resultat_id>")
def hamta_resultat(resultat_id):
    rad = get_db().execute("SELECT * FROM resultat WHERE id = ?", (resultat_id,)).fetchone()
    if rad is None:
        return fel(f"Resultat {resultat_id} finns inte.", 404)
    return jsonify(_resultat_json(rad))


@app.delete("/api/ladok/resultat/<int:resultat_id>")
def ta_bort_resultat(resultat_id):
    """Endast för prototypen (rensa testdata). I verkligheten kan resultat inte raderas."""
    db = get_db()
    resultat = db.execute("DELETE FROM resultat WHERE id = ?", (resultat_id,))
    db.commit()
    if resultat.rowcount == 0:
        return fel(f"Resultat {resultat_id} finns inte.", 404)
    return "", 204


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORTS["ladok"])
