"""Canvas (simulerad) - lärplattformen där uppgifter rättas och omdömen sätts.

Ingår inte i de tre tjänster som uppgiften kräver, men behövs för att kunna visa
"studenter med deras omdömen för vald uppgift". Motsvarar tjänsten Hämta resultat
(REST) från uppgift 2. Canvas känner bara användarnamn - aldrig personnummer.
"""
from flask import jsonify

import config
from common.service import fel, get_db, skapa_tjanst

app = skapa_tjanst("Canvas", __name__, "canvas.db")


@app.get("/api/canvas/kurser/<kurskod>/uppgifter")
def lista_uppgifter(kurskod):
    rader = get_db().execute(
        "SELECT id, namn FROM uppgift WHERE kurskod = ? ORDER BY id", (kurskod.strip().upper(),)
    ).fetchall()
    if not rader:
        return fel(f"Inga uppgifter hittades för kursen {kurskod.upper()} i Canvas.", 404)
    return jsonify(
        kurskod=kurskod.strip().upper(),
        uppgifter=[{"id": r["id"], "namn": r["namn"]} for r in rader],
    )


@app.get("/api/canvas/kurser/<kurskod>/uppgifter/<int:uppgift_id>/omdomen")
def hamta_omdomen(kurskod, uppgift_id):
    db = get_db()
    uppgift = db.execute(
        "SELECT id, namn FROM uppgift WHERE id = ? AND kurskod = ?",
        (uppgift_id, kurskod.strip().upper()),
    ).fetchone()
    if uppgift is None:
        return fel(f"Uppgift {uppgift_id} finns inte i kursen {kurskod.upper()}.", 404)
    rader = db.execute(
        "SELECT s.anvandarnamn, s.namn, i.omdome, i.bedomd_datum "
        "FROM inlamning i JOIN student s ON s.anvandarnamn = i.anvandarnamn "
        "WHERE i.uppgift_id = ? ORDER BY s.namn",
        (uppgift_id,),
    ).fetchall()
    return jsonify(
        uppgift={"id": uppgift["id"], "namn": uppgift["namn"]},
        omdomen=[
            {
                "anvandarnamn": r["anvandarnamn"],
                "namn": r["namn"],
                "omdome": r["omdome"],
                "bedomd_datum": r["bedomd_datum"],
            }
            for r in rader
        ],
    )


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORTS["canvas"])
