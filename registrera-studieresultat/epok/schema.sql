CREATE TABLE IF NOT EXISTS kurs (
    kurskod TEXT PRIMARY KEY,
    namn    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS modul (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    kurskod   TEXT NOT NULL REFERENCES kurs(kurskod) ON DELETE CASCADE,
    modul     TEXT NOT NULL,                       -- t.ex. '0005'
    benamning TEXT NOT NULL,                       -- t.ex. 'Inlämningsuppgift'
    hp        REAL NOT NULL CHECK (hp > 0),        -- högskolepoäng
    aktiv     INTEGER NOT NULL DEFAULT 1 CHECK (aktiv IN (0, 1)),
    UNIQUE (kurskod, modul)
);
