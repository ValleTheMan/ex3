-- Alla namn är PÅHITTADE testdata.
INSERT INTO uppgift (id, kurskod, namn) VALUES
    (101, 'D0031N', 'Inlämningsuppgift 1'),
    (102, 'D0031N', 'Inlämningsuppgift 2');

INSERT INTO student (anvandarnamn, namn) VALUES
    ('sveedz-4', 'Edvin Svensson'),
    ('anlisa-1', 'Lisa Andersson'),
    ('johmar-2', 'Marcus Johansson'),
    ('karsof-3', 'Sofia Karlsson'),
    ('niljoh-1', 'Johan Nilsson'),
    ('erialf-2', 'Alfred Eriksson'),
    ('lunmat-5', 'Matilda Lundgren'),
    ('holben-1', 'Bengt Holm');

INSERT INTO inlamning (uppgift_id, anvandarnamn, omdome, bedomd_datum) VALUES
    (101, 'sveedz-4', 'G',  '2026-11-10'),
    (101, 'anlisa-1', 'VG', '2026-11-10'),
    (101, 'johmar-2', 'U',  '2026-11-11'),
    (101, 'karsof-3', 'VG', '2026-11-11'),
    (101, 'niljoh-1', 'G',  '2026-11-12'),
    (101, 'erialf-2', NULL, NULL),
    (101, 'lunmat-5', 'G',  '2026-11-12'),
    (101, 'holben-1', 'G',  '2026-11-12'),
    (102, 'sveedz-4', 'G',  '2026-11-20'),
    (102, 'anlisa-1', 'G',  '2026-11-20'),
    (102, 'johmar-2', 'VG', '2026-11-21'),
    (102, 'niljoh-1', 'U',  '2026-11-21');
