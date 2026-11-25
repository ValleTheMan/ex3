CREATE TABLE IF NOT EXISTS student (
    anvandarnamn TEXT PRIMARY KEY COLLATE NOCASE,   -- t.ex. 'sveedz-4' (samma som i Canvas)
    personnummer TEXT NOT NULL UNIQUE               -- ÅÅÅÅMMDD-XXXX
);

-- Spårbarhet (privacy by design): varje uppslag av ett personnummer loggas.
CREATE TABLE IF NOT EXISTS atkomstlogg (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tidpunkt     TEXT NOT NULL DEFAULT (datetime('now')),
    anvandarnamn TEXT NOT NULL,
    anropare     TEXT NOT NULL,
    traff        INTEGER NOT NULL CHECK (traff IN (0, 1))
);
