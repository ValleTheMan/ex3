"""Resultat Canvas GUI - webbgränssnitt + orkestrering av REST-tjänsterna.

Webbläsaren pratar bara med den här appen. Appen anropar i sin tur:
    Epok        get_Modul          -> modulerna för kursen
    Canvas      omdömen            -> studenter och omdömen för vald uppgift
    StudentITS  get_Persnummer     -> personnummer per student
    Ladok       reg_Resultat       -> registrering av betyg

API-nyckeln och personnumren hanteras alltså på serversidan. Vid registrering
slås personnumret upp igen här, så att webbläsaren aldrig kan ange ett eget.
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests
from flask import jsonify, request, send_from_directory

import config
from common.service import fel, hamta_json, skapa_tjanst

app = skapa_tjanst("Resultat Canvas GUI", __name__, kraver_nyckel=False)

HUVUDEN = {"X-API-Key": config.API_KEY, "X-Caller": "resultat-canvas-gui"}
TIMEOUT_SEKUNDER = 5
MAX_POSTER = 500
TJANSTNAMN = {"epok": "Epok", "canvas": "Canvas", "studentits": "StudentITS", "ladok": "Ladok"}


class TjanstFel(Exception):
    """Fel vid anrop till ett av de underliggande systemen."""

    def __init__(self, meddelande, status_kod=502):
        super().__init__(meddelande)
        self.meddelande = meddelande
        self.status_kod = status_kod


@app.errorhandler(TjanstFel)
def hantera_tjanstfel(e):
    return fel(e.meddelande, e.status_kod)


# ------------------------------------------------------------------ hjälpfunktioner
def anropa(tjanst, metod, vag, **kwargs):
    """Gör ett HTTP-anrop till en tjänst och returnerar råsvaret."""
    try:
        return requests.request(
            metod, config.url(tjanst) + vag, headers=HUVUDEN, timeout=TIMEOUT_SEKUNDER, **kwargs
        )
    except requests.RequestException:
        raise TjanstFel(
            f"{TJANSTNAMN[tjanst]} svarar inte. Kontrollera att tjänsten är igång."
        ) from None


def json_ur(svar, tjanst):
    try:
        data = svar.json()
    except ValueError:
        raise TjanstFel(f"Ogiltigt svar från {TJANSTNAMN[tjanst]}.") from None
    return data if isinstance(data, dict) else {}


def anropa_json(tjanst, metod, vag, **kwargs):
    """Som anropa(), men returnerar JSON och kastar TjanstFel vid HTTP-fel."""
    svar = anropa(tjanst, metod, vag, **kwargs)
    data = json_ur(svar, tjanst)
    if svar.status_code >= 400:
        meddelande = data.get("meddelande", f"{TJANSTNAMN[tjanst]} svarade {svar.status_code}.")
        raise TjanstFel(meddelande, 404 if svar.status_code == 404 else 502)
    return data


def hamta_personnummer(anvandarnamn):
    """StudentITS get_Persnummer. Returnerar None om studenten saknas."""
    vag = f"/api/studentits/studenter/{quote(anvandarnamn, safe='')}/personnummer"
    svar = anropa("studentits", "GET", vag)
    if svar.status_code == 404:
        return None
    data = json_ur(svar, "studentits")
    if svar.status_code != 200 or "personnummer" not in data:
        raise TjanstFel(data.get("meddelande", "StudentITS kunde inte slå upp personnumret."))
    return data["personnummer"]


def hitta_uppgift(uppgifter, soktext):
    """Matchar användarens text mot uppgift (id, exakt namn eller unik delträff)."""
    s = soktext.strip().casefold()
    for u in uppgifter:
        if s == str(u["id"]) or s == u["namn"].casefold():
            return u
    traffar = [u for u in uppgifter if s in u["namn"].casefold()]
    return traffar[0] if len(traffar) == 1 else None


# ------------------------------------------------------------------ sidor och API
@app.get("/")
def startsida():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/gui/uppgifter")
def uppgifter():
    """Förslag till fältet 'Uppgift' (hämtas från Canvas)."""
    kurskod = request.args.get("kurskod", "").strip().upper()
    if not kurskod:
        return fel("Ange kurskod.", 400)
    data = anropa_json("canvas", "GET", f"/api/canvas/kurser/{quote(kurskod, safe='')}/uppgifter")
    return jsonify(uppgifter=data["uppgifter"])


@app.get("/api/gui/underlag")
def underlag():
    """Samlar allt som behövs för registreringsvyn (kurskod + uppgift -> moduler + studenter)."""
    kurskod = request.args.get("kurskod", "").strip().upper()
    uppgift_text = request.args.get("uppgift", "").strip()
    if not kurskod or not uppgift_text:
        return fel("Ange både kurskod och uppgift.", 400)
    k = quote(kurskod, safe="")

    # 1. Moduler från Epok (get_Modul)
    moduler = anropa_json("epok", "GET", f"/api/epok/kurser/{k}/moduler")

    # 2. Uppgift och omdömen från Canvas
    kursens_uppgifter = anropa_json("canvas", "GET", f"/api/canvas/kurser/{k}/uppgifter")["uppgifter"]
    uppgift = hitta_uppgift(kursens_uppgifter, uppgift_text)
    if uppgift is None:
        return fel(f"Uppgiften '{uppgift_text}' hittades inte i kursen {kurskod}.", 404)
    omdomen = anropa_json(
        "canvas", "GET", f"/api/canvas/kurser/{k}/uppgifter/{uppgift['id']}/omdomen"
    )["omdomen"]

    # 3. Betygsskala från Ladok
    skala = anropa_json("ladok", "GET", "/api/ladok/betygsskala")["betygsskala"]

    # 4. Personnummer från StudentITS (get_Persnummer), parallellt
    with ThreadPoolExecutor(max_workers=8) as pool:
        personnummer = list(pool.map(lambda o: hamta_personnummer(o["anvandarnamn"]), omdomen))

    studenter = []
    for o, pnr in zip(omdomen, personnummer):
        avvikelse = None
        if pnr is None:
            avvikelse = "Personnummer saknas i StudentITS."
        elif o["omdome"] is None:
            avvikelse = "Ingen bedömning i Canvas ännu."
        studenter.append({
            "anvandarnamn": o["anvandarnamn"],
            "namn": o["namn"],
            "omdome": o["omdome"],
            "personnummer": pnr,
            "avvikelse": avvikelse,
        })

    return jsonify(
        kurskod=moduler["kurskod"],
        kursnamn=moduler["kursnamn"],
        uppgift=uppgift,
        moduler=moduler["moduler"],
        betygsskala=skala,
        studenter=studenter,
    )


def registrera_en(kurskod, modul, post):
    """Registrerar ett resultat i Ladok. Returnerar alltid {anvandarnamn, status, meddelande}."""
    post = post if isinstance(post, dict) else {}
    anvandarnamn = str(post.get("anvandarnamn", "")).strip()

    def utfall(status, meddelande):
        return {"anvandarnamn": anvandarnamn, "status": status, "meddelande": meddelande}

    if not anvandarnamn:
        return utfall("hinder", "Användarnamn saknas.")
    try:
        personnummer = hamta_personnummer(anvandarnamn)
        if personnummer is None:
            return utfall("hinder", "Personnummer saknas i StudentITS.")
        svar = anropa("ladok", "POST", "/api/ladok/resultat", json={
            "personnummer": personnummer,
            "kurskod": kurskod,
            "modul": modul,
            "datum": str(post.get("datum", "")),
            "betyg": str(post.get("betyg", "")),
        })
        data = json_ur(svar, "ladok")
    except TjanstFel as e:
        return utfall("hinder", e.meddelande)
    if svar.status_code == 201:
        return utfall("registrerad", data.get("meddelande", "Registrerad i Ladok."))
    return utfall("hinder", data.get("meddelande", f"Ladok svarade {svar.status_code}."))


@app.post("/api/gui/registrera")
def registrera():
    """Registrerar valda studenters resultat i Ladok och returnerar ett utfall per student."""
    data = hamta_json()
    if data is None:
        return fel("Anropet måste innehålla ett JSON-objekt.", 400)
    kurskod = str(data.get("kurskod", "")).strip().upper()
    modul = str(data.get("modul", "")).strip()
    poster = data.get("resultat")
    if not kurskod or not modul:
        return fel("Kurskod och modul måste anges.", 400)
    if not isinstance(poster, list) or not poster:
        return fel("Inga resultat att registrera.", 400)
    if len(poster) > MAX_POSTER:
        return fel(f"Högst {MAX_POSTER} resultat kan registreras åt gången.", 400)

    # Modulen måste vara en aktiv modul i Epok för kursen.
    aktiva = anropa_json("epok", "GET", f"/api/epok/kurser/{quote(kurskod, safe='')}/moduler")
    if modul not in {m["modul"] for m in aktiva["moduler"]}:
        return fel(f"Modul {modul} är inte en aktiv modul i kursen {kurskod}.", 422)

    utfall = [registrera_en(kurskod, modul, p) for p in poster]
    registrerade = sum(1 for u in utfall if u["status"] == "registrerad")
    return jsonify(
        kurskod=kurskod,
        modul=modul,
        resultat=utfall,
        sammanfattning={"registrerade": registrerade, "hinder": len(utfall) - registrerade},
    )


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORTS["gui"])
