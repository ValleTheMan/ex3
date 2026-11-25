# Registrera studieresultat – REST Web Services (D0031N, Examinationsuppgift 3)

Prototyp som bygger vidare på SOA-lösningen i Examinationsuppgift 2. Läraren anger kurskod och uppgift,
modulerna och studenternas omdömen hämtas, personnumren slås upp, och resultaten registreras i Ladok
– allt via REST-webbtjänster som pratar JSON.

## Arkitektur

```
 Webbläsare
     │  (HTML/JS)
     ▼
 ┌──────────────────────┐   get_Modul        ┌────────────┐
 │  Resultat Canvas GUI │ ─────────────────► │ Epok       │ :5001  epok.db
 │  (Flask, port 5000)  │   omdömen          ├────────────┤
 │                      │ ─────────────────► │ Canvas*    │ :5004  canvas.db
 │  orkestrerar         │   get_Persnummer   ├────────────┤
 │  tjänsterna          │ ─────────────────► │ StudentITS │ :5002  studentits.db
 │                      │   reg_Resultat     ├────────────┤
 │                      │ ─────────────────► │ Ladok      │ :5003  ladok.db
 └──────────────────────┘                    └────────────┘
```

\* Canvas är en liten simulator (motsvarar tjänsten *Hämta resultat* i uppgift 2). Den behövs för att kunna visa
"studenter med deras omdömen för vald uppgift", men ingår inte bland de tre tjänster som uppgiften kräver.

Varje "system" är en **egen Flask-app med egen SQLite-databas** och kan startas för sig. Alla ligger i samma
projekt, precis som uppgiften tillåter.

| Krav i uppgiften | Var det uppfylls |
|---|---|
| Epok: `get_Modul` (kurskod → aktiva moduler) | `epok/app.py`, `GET /api/epok/kurser/{kurskod}/moduler` |
| StudentITS: `get_Persnummer` (användarnamn → personnummer) | `studentits/app.py`, `GET /api/studentits/studenter/{anvandarnamn}/personnummer` |
| Ladok: `reg_Resultat` (lagrar, returnerar status) | `ladok/app.py`, `POST /api/ladok/resultat` → `registrerad` / `hinder` |
| Användargränssnitt (Resultat Canvas GUI) | `gui/` (`app.py` + `static/`) |
| HTTP-metoder GET/POST/PUT/DELETE | Epok har alla fyra, Ladok har GET/POST/DELETE |
| JSON mellan tjänsterna | Alla svar och anrop är JSON |
| Data skild från programkod | `schema.sql` och `seed.sql` per tjänst; koden innehåller ingen testdata |
| Fristående tjänster med tydliga gränssnitt | Egna processer, portar och databaser; enda kopplingen är HTTP |

## Kom igång

Kräver Python 3.10 eller senare.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run_all.py                  # startar alla fem processerna
```

Öppna sedan <http://127.0.0.1:5000>. Avsluta med Ctrl+C.
`python run_all.py --aterstall` raderar databaserna och skapar om dem från `seed.sql`.

Kör alltid kommandon från projektets rotmapp. En enskild tjänst startas med t.ex. `python -m ladok.app`.

### Tester

```bash
python -m unittest tests.test_tjanster -v   # enhetstester, inga servrar behövs
python tests/e2e_smoke.py                   # helhetstest, kräver att run_all.py körs
```

## Demo i gränssnittet

1. Kurskod `D0031N`, uppgift `Inlämningsuppgift 1` → **Hämta studenter**.
2. Välj modul (t.ex. `0005 Inlämningsuppgift`), ange examinationsdatum, kontrollera betygen.
3. **Registrera i Ladok**. Varje rad får status *Registrerad* eller *Hinder* med förklaring.

Testdatan är gjord för att visa både lyckade och misslyckade fall:

| Student | Vad som händer |
|---|---|
| sveedz-4, anlisa-1, niljoh-1, johmar-2 | Registreras utan problem |
| karsof-3 | *Hinder*: modul 0005 har redan ett registrerat resultat i Ladok |
| lunmat-5 | *Hinder*: saknar registrering på kursen i Ladok |
| holben-1 | *Avvikelse*: finns i Canvas men saknas i StudentITS (personnummer kan inte hämtas) |
| erialf-2 | *Avvikelse*: ingen bedömning i Canvas ännu |

Om du registrerar samma modul igen får du *Hinder* (redan registrerat). Kör `--aterstall` för att börja om.
Alla namn och personnummer är påhittade.

## API-specifikation

Alla anrop (utom `GET /health`) kräver headern `X-API-Key: ltu-dev-nyckel` (ändras med miljövariabeln `LTU_API_KEY`).
Fel returneras som `{"status": "fel", "meddelande": "..."}` (Ladok använder `"status": "hinder"`).

### Epok (port 5001)

| Metod | Sökväg | Beskrivning |
|---|---|---|
| GET | `/api/epok/kurser` | Lista kurser |
| GET | `/api/epok/kurser/{kurskod}/moduler` | **get_Modul** – kursens aktiva moduler (404 om kursen saknas) |
| POST | `/api/epok/kurser/{kurskod}/moduler` | Skapa modul `{modul, benamning, hp, aktiv?}` → 201 / 409 |
| PUT | `/api/epok/kurser/{kurskod}/moduler/{modul}` | Ändra `benamning`, `hp`, `aktiv` |
| DELETE | `/api/epok/kurser/{kurskod}/moduler/{modul}` | Ta bort modul → 204 |

```json
GET /api/epok/kurser/D0031N/moduler
{"kurskod": "D0031N", "kursnamn": "Enterprise Architecture och SOA",
 "moduler": [{"modul": "0005", "benamning": "Inlämningsuppgift", "hp": 3.0, "aktiv": true}]}
```

### StudentITS (port 5002)

| Metod | Sökväg | Beskrivning |
|---|---|---|
| GET | `/api/studentits/studenter/{anvandarnamn}/personnummer` | **get_Persnummer** → `{"anvandarnamn": "sveedz-4", "personnummer": "19940613-2345"}` (404 om okänd) |
| GET | `/api/studentits/atkomstlogg?limit=50` | Logg över uppslag (utan personnummer) |

### Ladok (port 5003)

| Metod | Sökväg | Beskrivning |
|---|---|---|
| POST | `/api/ladok/resultat` | **reg_Resultat** |
| GET | `/api/ladok/resultat?personnummer=&kurskod=&modul=` | Hämta registrerade resultat |
| GET | `/api/ladok/resultat/{id}` | Ett resultat |
| DELETE | `/api/ladok/resultat/{id}` | Endast för prototypen (rensa testdata) |
| GET | `/api/ladok/betygsskala` | Giltiga betyg (U, G, VG, 3, 4, 5) |

```json
POST /api/ladok/resultat
{"personnummer": "19940613-2345", "kurskod": "D0031N", "modul": "0005", "datum": "2026-11-20", "betyg": "G"}

201 → {"status": "registrerad", "meddelande": "Resultatet har registrerats i Ladok.", "resultat": {...}}
409 → {"status": "hinder", "meddelande": "Modul 0005 har redan ett registrerat resultat (G, 2026-10-12)."}
```

Ladok kontrollerar: obligatoriska fält (400), format på personnummer/kurskod/modul/datum (422), att datumet inte
ligger i framtiden (422), att betyget finns i skalan (422), att studenten är registrerad på kursen (422) och att
modulen inte redan har ett resultat (409).

### Canvas, simulerad (port 5004)

| Metod | Sökväg | Beskrivning |
|---|---|---|
| GET | `/api/canvas/kurser/{kurskod}/uppgifter` | Kursens uppgifter |
| GET | `/api/canvas/kurser/{kurskod}/uppgifter/{id}/omdomen` | Studenter och omdömen (G/VG/U eller null) |

### GUI (port 5000)

| Metod | Sökväg | Beskrivning |
|---|---|---|
| GET | `/api/gui/uppgifter?kurskod=` | Uppgiftsförslag |
| GET | `/api/gui/underlag?kurskod=&uppgift=` | Moduler + studenter + omdömen + personnummer |
| POST | `/api/gui/registrera` | `{kurskod, modul, resultat: [{anvandarnamn, datum, betyg}]}` → utfall per student |

## Kopplingen till uppgift 2 (SOA)

- **Resultatportalen som orkestrerare**: `gui/app.py` motsvarar *Validering & sammanställning* – den hämtar,
  kopplar ihop och kontrollerar data innan Ladok anropas.
- **ID-mappning (GDPR)**: personnummer hämtas bara system-till-system. Webbläsaren skickar enbart användarnamn;
  servern slår upp personnumret igen vid registrering, så att inget personnummer kan manipuleras från klienten.
  Personnumren är maskerade i tabellen tills man kryssar i *Visa personnummer*, och varje uppslag loggas i StudentITS.
- **Behörighet/API-gateway**: `X-API-Key` är en förenklad motsvarighet till gatewayen i uppgift 2.
- **Avvikelsehantering**: studenter som inte kan matchas (saknat personnummer, ingen bedömning) flaggas och
  väljs bort automatiskt – i uppgift 2 kallas detta *Hantera avvikelser*. Ladoks *hinder* visas per rad.
- **Löst kopplade system**: byter man ut Canvas behöver bara `/api/gui/underlag` peka mot en annan tjänst.

## Begränsningar (prototypen)

- Personnummer kontrolleras bara till formatet, inte kontrollsiffran.
- Ingen riktig inloggning/SSO och ingen attestering (examinatorns steg) – uppgiften avgränsar till registreringen.
- Flask-utvecklingsservern och en delad API-nyckel är inte avsedda för produktion.
- Exempeldatan för moduler i `epok/seed.sql` är påhittad; justera den efter den riktiga kursplanen.

## Filer

```
config.py            portar, nyckel, datamapp
run_all.py           startar allt
common/service.py    gemensam Flask-grund (databas, API-nyckel, felsvar)
epok/  studentits/  ladok/  canvas/     app.py + schema.sql + seed.sql
gui/app.py           orkestrering    gui/static/   index.html, styles.css, app.js
tests/               enhetstester och helhetstest
```
# ex3
