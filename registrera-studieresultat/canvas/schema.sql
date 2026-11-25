CREATE TABLE IF NOT EXISTS uppgift (
    id      INTEGER PRIMARY KEY,
    kurskod TEXT NOT NULL,
    namn    TEXT NOT NULL,
    UNIQUE (kurskod, namn)
);

CREATE TABLE IF NOT EXISTS student (
    anvandarnamn TEXT PRIMARY KEY COLLATE NOCASE,   -- Canvas känner bara användarnamn, inte personnummer
    namn         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inlamning (
    uppgift_id   INTEGER NOT NULL REFERENCES uppgift(id) ON DELETE CASCADE,
    anvandarnamn TEXT NOT NULL REFERENCES student(anvandarnamn),
    omdome       TEXT CHECK (omdome IN ('U', 'G', 'VG')),   -- NULL = ännu inte bedömd
    bedomd_datum TEXT,
    PRIMARY KEY (uppgift_id, anvandarnamn)
);
