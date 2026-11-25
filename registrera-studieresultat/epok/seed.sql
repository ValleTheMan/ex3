-- Exempeldata. Justera gärna så att den matchar den riktiga kursplanen (figur 1 i uppgiften).
INSERT INTO kurs (kurskod, namn) VALUES
    ('D0031N', 'Enterprise Architecture och SOA');

INSERT INTO modul (kurskod, modul, benamning, hp, aktiv) VALUES
    ('D0031N', '0001', 'Seminarier',          1.5, 1),
    ('D0031N', '0002', 'Skriftlig tentamen',  3.0, 1),
    ('D0031N', '0004', 'Laboration (utgången modul)', 1.5, 0),
    ('D0031N', '0005', 'Inlämningsuppgift',   3.0, 1);
