INSERT INTO betygsskala (kod, beskrivning) VALUES
    ('U',  'Underkänd'),
    ('G',  'Godkänd'),
    ('VG', 'Väl godkänd'),
    ('3',  'Betyg 3'),
    ('4',  'Betyg 4'),
    ('5',  'Betyg 5');

-- Alla utom 19970819-6621 (lunmat-5) är registrerade på D0031N => "hinder" för henne.
INSERT INTO kursregistrering (personnummer, kurskod) VALUES
    ('19940613-2345', 'D0031N'),
    ('19960228-1122', 'D0031N'),
    ('19930907-4410', 'D0031N'),
    ('19981115-7783', 'D0031N'),
    ('19950321-9056', 'D0031N'),
    ('19990102-3347', 'D0031N');

-- Sofia (karsof-3) har redan ett registrerat resultat på modul 0005 => "hinder" vid ny registrering.
INSERT INTO resultat (personnummer, kurskod, modul, betyg, examinationsdatum) VALUES
    ('19981115-7783', 'D0031N', '0005', 'G', '2026-10-12');
