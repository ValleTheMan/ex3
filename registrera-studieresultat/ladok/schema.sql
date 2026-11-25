CREATE TABLE IF NOT EXISTS betygsskala (
    kod         TEXT PRIMARY KEY,
    beskrivning TEXT NOT NULL
);

-- Vilka studenter som är registrerade på vilken kurs.
CREATE TABLE IF NOT EXISTS kursregistrering (
    personnummer TEXT NOT NULL,
    kurskod      TEXT NOT NULL,
    PRIMARY KEY (personnummer, kurskod)
);

CREATE TABLE IF NOT EXISTS resultat (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    personnummer      TEXT NOT NULL,
    kurskod           TEXT NOT NULL,
    modul             TEXT NOT NULL,
    betyg             TEXT NOT NULL REFERENCES betygsskala(kod),
    examinationsdatum TEXT NOT NULL,                       -- ÅÅÅÅ-MM-DD
    registrerad       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (personnummer, kurskod, modul)                  -- ett betyg per modul
);
