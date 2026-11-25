"""Enhetstester för de fyra tjänsterna (körs utan att några servrar startas).

    python -m unittest tests.test_tjanster -v
"""
import os
import shutil
import tempfile

# Använd en tillfällig datamapp så att tester aldrig rör de riktiga databaserna.
_TMP = tempfile.mkdtemp(prefix="ltu-test-")
os.environ["LTU_DATA_DIR"] = _TMP

import unittest  # noqa: E402
from datetime import date, timedelta  # noqa: E402

import config  # noqa: E402
from canvas.app import app as canvas_app  # noqa: E402
from epok.app import app as epok_app  # noqa: E402
from ladok.app import app as ladok_app  # noqa: E402
from studentits.app import app as studentits_app  # noqa: E402

NYCKEL = {"X-API-Key": config.API_KEY}


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


class EpokTest(unittest.TestCase):
    def setUp(self):
        self.k = epok_app.test_client()

    def test_get_modul_returnerar_bara_aktiva_moduler(self):
        svar = self.k.get("/api/epok/kurser/D0031N/moduler", headers=NYCKEL)
        self.assertEqual(svar.status_code, 200)
        koder = [m["modul"] for m in svar.get_json()["moduler"]]
        self.assertIn("0005", koder)
        self.assertNotIn("0004", koder)  # inaktiv modul ska inte vara med

    def test_kurskod_ar_skiftlageskanslig_inte(self):
        svar = self.k.get("/api/epok/kurser/d0031n/moduler", headers=NYCKEL)
        self.assertEqual(svar.status_code, 200)

    def test_okand_kurs_ger_404(self):
        svar = self.k.get("/api/epok/kurser/XXXX99/moduler", headers=NYCKEL)
        self.assertEqual(svar.status_code, 404)

    def test_utan_api_nyckel_ger_401(self):
        self.assertEqual(self.k.get("/api/epok/kurser/D0031N/moduler").status_code, 401)

    def test_crud_pa_modul(self):
        bas = "/api/epok/kurser/D0031N/moduler"
        skapa = self.k.post(bas, json={"modul": "0009", "benamning": "Test", "hp": 1.5}, headers=NYCKEL)
        self.assertEqual(skapa.status_code, 201)
        dubblett = self.k.post(bas, json={"modul": "0009", "benamning": "Test", "hp": 1.5}, headers=NYCKEL)
        self.assertEqual(dubblett.status_code, 409)
        andra = self.k.put(f"{bas}/0009", json={"hp": 2.0, "aktiv": False}, headers=NYCKEL)
        self.assertEqual(andra.status_code, 200)
        self.assertEqual(andra.get_json()["hp"], 2.0)
        self.assertEqual(self.k.delete(f"{bas}/0009", headers=NYCKEL).status_code, 204)
        self.assertEqual(self.k.delete(f"{bas}/0009", headers=NYCKEL).status_code, 404)

    def test_ogiltig_modul_ger_400(self):
        svar = self.k.post("/api/epok/kurser/D0031N/moduler",
                           json={"modul": "5", "benamning": "X", "hp": 1}, headers=NYCKEL)
        self.assertEqual(svar.status_code, 400)


class StudentItsTest(unittest.TestCase):
    def setUp(self):
        self.k = studentits_app.test_client()

    def test_get_persnummer(self):
        svar = self.k.get("/api/studentits/studenter/sveedz-4/personnummer", headers=NYCKEL)
        self.assertEqual(svar.status_code, 200)
        self.assertEqual(svar.get_json()["personnummer"], "19940613-2345")

    def test_okand_student_ger_404(self):
        svar = self.k.get("/api/studentits/studenter/holben-1/personnummer", headers=NYCKEL)
        self.assertEqual(svar.status_code, 404)

    def test_uppslag_loggas_utan_personnummer(self):
        self.k.get("/api/studentits/studenter/anlisa-1/personnummer",
                   headers={**NYCKEL, "X-Caller": "enhetstest"})
        logg = self.k.get("/api/studentits/atkomstlogg?limit=5", headers=NYCKEL).get_json()["logg"]
        self.assertTrue(any(p["anropare"] == "enhetstest" and p["anvandarnamn"] == "anlisa-1" for p in logg))
        self.assertNotIn("personnummer", logg[0])

    def test_utan_api_nyckel_ger_401(self):
        svar = self.k.get("/api/studentits/studenter/sveedz-4/personnummer")
        self.assertEqual(svar.status_code, 401)


class LadokTest(unittest.TestCase):
    def setUp(self):
        self.k = ladok_app.test_client()
        self.skapade = []

    def tearDown(self):
        for rid in self.skapade:
            self.k.delete(f"/api/ladok/resultat/{rid}", headers=NYCKEL)

    def reg(self, **andringar):
        post = {"personnummer": "19960228-1122", "kurskod": "D0031N", "modul": "0001",
                "datum": "2026-11-01", "betyg": "G"}
        post.update(andringar)
        return self.k.post("/api/ladok/resultat", json=post, headers=NYCKEL)

    def test_lyckad_registrering(self):
        svar = self.reg()
        self.assertEqual(svar.status_code, 201)
        data = svar.get_json()
        self.assertEqual(data["status"], "registrerad")
        self.skapade.append(data["resultat"]["id"])
        # Resultatet ska gå att hämta igen från databasen
        hamtat = self.k.get(f"/api/ladok/resultat/{data['resultat']['id']}", headers=NYCKEL)
        self.assertEqual(hamtat.get_json()["betyg"], "G")

    def test_dubbelregistrering_ger_hinder_409(self):
        forsta = self.reg(modul="0002")
        self.skapade.append(forsta.get_json()["resultat"]["id"])
        andra = self.reg(modul="0002", betyg="VG")
        self.assertEqual(andra.status_code, 409)
        self.assertEqual(andra.get_json()["status"], "hinder")

    def test_redan_registrerat_i_testdata(self):
        svar = self.reg(personnummer="19981115-7783", modul="0005")
        self.assertEqual(svar.status_code, 409)

    def test_student_utan_kursregistrering_ger_hinder(self):
        svar = self.reg(personnummer="19970819-6621")
        self.assertEqual(svar.status_code, 422)
        self.assertIn("saknar registrering", svar.get_json()["meddelande"])

    def test_ogiltigt_betyg(self):
        self.assertEqual(self.reg(betyg="X").status_code, 422)

    def test_datum_i_framtiden(self):
        morgon = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(self.reg(datum=morgon).status_code, 422)

    def test_felaktigt_datumformat(self):
        self.assertEqual(self.reg(datum="01/11/2026").status_code, 422)

    def test_felaktigt_personnummerformat(self):
        self.assertEqual(self.reg(personnummer="940613-2345").status_code, 422)

    def test_saknade_falt_ger_400(self):
        svar = self.k.post("/api/ladok/resultat", json={"personnummer": "19960228-1122"}, headers=NYCKEL)
        self.assertEqual(svar.status_code, 400)
        self.assertEqual(svar.get_json()["status"], "hinder")

    def test_ogiltig_json_ger_400(self):
        svar = self.k.post("/api/ladok/resultat", data="inte json",
                           headers={**NYCKEL, "Content-Type": "application/json"})
        self.assertEqual(svar.status_code, 400)

    def test_betygsskala(self):
        koder = [b["kod"] for b in self.k.get("/api/ladok/betygsskala", headers=NYCKEL).get_json()["betygsskala"]]
        self.assertEqual(koder[:3], ["U", "G", "VG"])


class CanvasTest(unittest.TestCase):
    def setUp(self):
        self.k = canvas_app.test_client()

    def test_uppgifter_och_omdomen(self):
        uppg = self.k.get("/api/canvas/kurser/D0031N/uppgifter", headers=NYCKEL).get_json()["uppgifter"]
        self.assertEqual(uppg[0]["namn"], "Inlämningsuppgift 1")
        om = self.k.get(f"/api/canvas/kurser/D0031N/uppgifter/{uppg[0]['id']}/omdomen",
                        headers=NYCKEL).get_json()["omdomen"]
        self.assertEqual(len(om), 8)
        self.assertNotIn("personnummer", om[0])  # Canvas känner inte till personnummer

    def test_okand_uppgift_ger_404(self):
        self.assertEqual(self.k.get("/api/canvas/kurser/D0031N/uppgifter/999/omdomen",
                                    headers=NYCKEL).status_code, 404)


if __name__ == "__main__":
    unittest.main()
