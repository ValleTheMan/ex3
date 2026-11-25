"""Helhetstest mot de KÖRANDE tjänsterna (starta först:  python run_all.py).

    python tests/e2e_smoke.py

Går igenom hela flödet via GUI:ts API: hämta underlag -> registrera -> kontrollera i Ladok.
Städar efter sig genom att ta bort de resultat som testet själv skapade.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

GUI = config.url("gui")
LADOK = config.url("ladok")
NYCKEL = {"X-API-Key": config.API_KEY}
antal_fel = 0


def kontrollera(beskrivning, villkor):
    global antal_fel
    print(("  OK   " if villkor else "  FEL  ") + beskrivning)
    if not villkor:
        antal_fel += 1


def main():
    print("1. Hämta underlag (Epok + Canvas + StudentITS + Ladok)")
    r = requests.get(f"{GUI}/api/gui/underlag",
                     params={"kurskod": "D0031N", "uppgift": "Inlämningsuppgift 1"}, timeout=10)
    kontrollera("GUI svarar 200", r.status_code == 200)
    u = r.json()
    koder = [m["modul"] for m in u["moduler"]]
    kontrollera("moduler från Epok innehåller 0005 men inte inaktiva 0004", "0005" in koder and "0004" not in koder)
    kontrollera("8 studenter hämtades från Canvas", len(u["studenter"]) == 8)
    per_namn = {s["anvandarnamn"]: s for s in u["studenter"]}
    kontrollera("personnummer hämtades för sveedz-4", per_namn["sveedz-4"]["personnummer"] == "19940613-2345")
    kontrollera("holben-1 flaggas som avvikelse (saknas i StudentITS)", per_namn["holben-1"]["avvikelse"] is not None)
    kontrollera("erialf-2 flaggas som avvikelse (ej bedömd)", per_namn["erialf-2"]["avvikelse"] is not None)

    print("2. Okänd kurs / uppgift ger begripliga fel")
    kontrollera("okänd kurs ger 404",
                requests.get(f"{GUI}/api/gui/underlag", params={"kurskod": "NOPE99", "uppgift": "x"}).status_code == 404)
    kontrollera("okänd uppgift ger 404",
                requests.get(f"{GUI}/api/gui/underlag", params={"kurskod": "D0031N", "uppgift": "finns inte"}).status_code == 404)

    print("3. Registrera i Ladok")
    igar = (date.today() - timedelta(days=1)).isoformat()
    morgon = (date.today() + timedelta(days=1)).isoformat()
    poster = [
        {"anvandarnamn": "sveedz-4", "datum": igar, "betyg": "G"},     # ska gå bra
        {"anvandarnamn": "anlisa-1", "datum": igar, "betyg": "VG"},    # ska gå bra
        {"anvandarnamn": "karsof-3", "datum": igar, "betyg": "G"},     # redan registrerad (seed)
        {"anvandarnamn": "lunmat-5", "datum": igar, "betyg": "G"},     # saknar kursregistrering
        {"anvandarnamn": "holben-1", "datum": igar, "betyg": "G"},     # saknas i StudentITS
        {"anvandarnamn": "johmar-2", "datum": morgon, "betyg": "U"},   # datum i framtiden
        {"anvandarnamn": "niljoh-1", "datum": igar, "betyg": "X"},     # ogiltigt betyg
    ]
    r = requests.post(f"{GUI}/api/gui/registrera",
                      json={"kurskod": "D0031N", "modul": "0005", "resultat": poster}, timeout=10)
    kontrollera("GUI svarar 200", r.status_code == 200)
    utfall = {x["anvandarnamn"]: x for x in r.json()["resultat"]}
    kontrollera("sveedz-4 registrerad", utfall["sveedz-4"]["status"] == "registrerad")
    kontrollera("anlisa-1 registrerad", utfall["anlisa-1"]["status"] == "registrerad")
    for namn in ("karsof-3", "lunmat-5", "holben-1", "johmar-2", "niljoh-1"):
        kontrollera(f"{namn} stoppas: {utfall[namn]['meddelande']}", utfall[namn]["status"] == "hinder")

    print("4. Verifiera i Ladok och städa")
    lista = requests.get(f"{LADOK}/api/ladok/resultat", params={"kurskod": "D0031N", "modul": "0005"},
                         headers=NYCKEL).json()["resultat"]
    mina = [x for x in lista if x["personnummer"] in ("19940613-2345", "19960228-1122")]
    kontrollera("två resultat finns lagrade i Ladok", len(mina) == 2)
    for x in mina:
        requests.delete(f"{LADOK}/api/ladok/resultat/{x['id']}", headers=NYCKEL)

    print("5. Ogiltig modul stoppas")
    r = requests.post(f"{GUI}/api/gui/registrera", json={
        "kurskod": "D0031N", "modul": "0004",
        "resultat": [{"anvandarnamn": "sveedz-4", "datum": igar, "betyg": "G"}]})
    kontrollera("inaktiv modul 0004 ger 422", r.status_code == 422)

    print(f"\n{'ALLT OK' if antal_fel == 0 else str(antal_fel) + ' KONTROLLER MISSLYCKADES'}")
    sys.exit(1 if antal_fel else 0)


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectionError:
        print("Kunde inte ansluta - är tjänsterna igång? Starta med: python run_all.py")
        sys.exit(2)
