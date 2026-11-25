"use strict";

const $ = (id) => document.getElementById(id);
const idag = () => new Date().toLocaleDateString("sv-SE"); // ÅÅÅÅ-MM-DD

// Allt som hämtats för den aktuella vyn. Varje rad har även referenser till sina DOM-element.
const tillstand = { kurskod: "", betygsskala: [], rader: [] };

// ------------------------------------------------------------------ hjälpfunktioner
function visaMeddelande(text, typ = "info") {
  const el = $("meddelande");
  el.textContent = text;
  el.className = `meddelande ${typ}`;
  el.hidden = !text;
}

async function hamtaJson(url, options) {
  const svar = await fetch(url, options);
  let data = null;
  try { data = await svar.json(); } catch { /* svaret saknar JSON */ }
  if (!svar.ok) throw new Error((data && data.meddelande) || `Något gick fel (${svar.status}).`);
  return data;
}

function element(tagg, egenskaper = {}, ...barn) {
  const el = document.createElement(tagg);
  Object.assign(el, egenskaper);
  el.append(...barn);
  return el;
}

const maskera = (pnr) => pnr.replace(/-\d{4}$/, "-****");
const formatHp = (hp) => String(hp).replace(".", ",");

function upptagen(knapp, ar, text) {
  if (ar) { knapp.dataset.text = knapp.textContent; knapp.textContent = text; }
  else if (knapp.dataset.text) { knapp.textContent = knapp.dataset.text; }
  knapp.disabled = ar;
}

// ------------------------------------------------------------------ hämta studenter
async function laddaUppgiftsforslag() {
  const kurskod = $("kurskod").value.trim();
  const lista = $("uppgiftslista");
  lista.replaceChildren();
  if (!kurskod) return;
  try {
    const data = await hamtaJson(`/api/gui/uppgifter?kurskod=${encodeURIComponent(kurskod)}`);
    for (const u of data.uppgifter) lista.append(element("option", { value: u.namn }));
  } catch { /* förslagen är valfria */ }
}

async function hamtaUnderlag(handelse) {
  handelse.preventDefault();
  visaMeddelande("");
  const kurskod = $("kurskod").value.trim();
  const uppgift = $("uppgift").value.trim();
  const knapp = $("hamta");
  upptagen(knapp, true, "Hämtar …");
  try {
    const data = await hamtaJson(
      `/api/gui/underlag?kurskod=${encodeURIComponent(kurskod)}&uppgift=${encodeURIComponent(uppgift)}`
    );
    tillstand.kurskod = data.kurskod;
    tillstand.betygsskala = data.betygsskala;

    $("resultatrubrik").replaceChildren(
      `${data.kurskod} ${data.kursnamn}`, " ",
      element("span", { className: "dov" }, `– ${data.uppgift.namn}`)
    );
    ritaModuler(data.moduler);
    ritaStudenter(data.studenter);
    $("datum").value = idag();
    $("datum").max = idag();
    $("resultatyta").hidden = false;

    const avvikelser = data.studenter.filter((s) => s.avvikelse).length;
    if (data.studenter.length === 0) {
      visaMeddelande("Uppgiften har inga inlämningar än.", "varning");
    } else if (avvikelser) {
      visaMeddelande(
        `${avvikelser} av ${data.studenter.length} studenter kan inte registreras och behöver hanteras manuellt.`,
        "varning"
      );
    }
  } catch (fel) {
    $("resultatyta").hidden = true;
    visaMeddelande(fel.message, "fel");
  } finally {
    upptagen(knapp, false);
  }
}

function ritaModuler(moduler) {
  const val = $("modul");
  val.replaceChildren(element("option", { value: "", textContent: "Välj modul" }));
  for (const m of moduler) {
    val.append(element("option", {
      value: m.modul,
      textContent: `${m.modul} ${m.benamning} (${formatHp(m.hp)} hp)`,
    }));
  }
  if (moduler.length === 1) val.value = moduler[0].modul;
}

// ------------------------------------------------------------------ tabellen
function ritaStudenter(studenter) {
  const tbody = $("studentrader");
  tbody.replaceChildren();
  tillstand.rader = [];
  $("markera-alla").checked = false;

  for (const s of studenter) {
    const kanRegistreras = !s.avvikelse;
    const rad = { ...s, registrerad: false, el: {} };

    rad.el.valj = element("input", { type: "checkbox", checked: kanRegistreras, disabled: !kanRegistreras });
    rad.el.valj.setAttribute("aria-label", `Välj ${s.namn}`);
    rad.el.valj.addEventListener("change", uppdateraAntal);

    rad.el.personnummer = element("td", { className: "siffror" });

    rad.el.datum = element("input", { type: "date", value: idag(), max: idag(), disabled: !kanRegistreras });
    rad.el.datum.setAttribute("aria-label", `Examinationsdatum för ${s.namn}`);

    rad.el.betyg = element("select", { disabled: !kanRegistreras });
    rad.el.betyg.setAttribute("aria-label", `Betyg för ${s.namn}`);
    rad.el.betyg.append(element("option", { value: "", textContent: "Välj betyg" }));
    for (const b of tillstand.betygsskala) {
      rad.el.betyg.append(element("option", { value: b.kod, textContent: b.kod, title: b.beskrivning }));
    }
    if (s.omdome && tillstand.betygsskala.some((b) => b.kod === s.omdome)) rad.el.betyg.value = s.omdome;

    rad.el.status = element("td");
    rad.el.tr = element("tr", {},
      element("td", { className: "smal" }, rad.el.valj),
      element("td", {}, s.namn, element("span", { className: "under", textContent: s.anvandarnamn })),
      rad.el.personnummer,
      element("td", {}, s.omdome || "–"),
      element("td", {}, rad.el.datum),
      element("td", {}, rad.el.betyg),
      rad.el.status
    );
    tbody.append(rad.el.tr);
    tillstand.rader.push(rad);

    if (s.avvikelse) visaStatus(rad, "avvikelse", s.avvikelse);
  }
  uppdateraPersonnummer();
  uppdateraAntal();
}

function uppdateraPersonnummer() {
  const visa = $("visa-pnr").checked;
  for (const rad of tillstand.rader) {
    rad.el.personnummer.textContent = rad.personnummer ? (visa ? rad.personnummer : maskera(rad.personnummer)) : "saknas";
  }
}

function visaStatus(rad, status, meddelande) {
  const rubrik = { registrerad: "Registrerad", hinder: "Hinder", avvikelse: "Avvikelse" }[status];
  const klass = status === "registrerad" ? "ok" : status;
  rad.el.status.replaceChildren(
    element("span", { className: `etikett ${klass}`, textContent: rubrik }),
    element("span", { className: "under", textContent: meddelande })
  );
  if (status === "registrerad") {
    rad.registrerad = true;
    rad.el.tr.classList.add("klar");
    for (const f of [rad.el.valj, rad.el.datum, rad.el.betyg]) f.disabled = true;
    rad.el.valj.checked = false;
  }
}

function uppdateraAntal() {
  const valda = tillstand.rader.filter((r) => r.el.valj.checked && !r.el.valj.disabled).length;
  $("antal").textContent = valda === 1 ? "1 student vald" : `${valda} studenter valda`;
}

// ------------------------------------------------------------------ registrera i Ladok
async function registrera() {
  visaMeddelande("");
  const modul = $("modul").value;
  const valda = tillstand.rader.filter((r) => r.el.valj.checked && !r.el.valj.disabled);

  if (!modul) return visaMeddelande("Välj en modul innan du registrerar.", "varning");
  if (valda.length === 0) return visaMeddelande("Välj minst en student att registrera.", "varning");

  let saknasUppgift = false;
  for (const rad of valda) {
    const datum = rad.el.datum.value;
    if (!datum || !rad.el.betyg.value) {
      visaStatus(rad, "hinder", "Fyll i både datum och betyg.");
      saknasUppgift = true;
    } else if (datum > idag()) {
      visaStatus(rad, "hinder", "Datumet får inte ligga i framtiden.");
      saknasUppgift = true;
    }
  }
  if (saknasUppgift) return visaMeddelande("Rätta de markerade raderna och försök igen.", "varning");

  const knapp = $("registrera");
  upptagen(knapp, true, "Registrerar …");
  try {
    const data = await hamtaJson("/api/gui/registrera", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kurskod: tillstand.kurskod,
        modul,
        resultat: valda.map((r) => ({
          anvandarnamn: r.anvandarnamn,
          datum: r.el.datum.value,
          betyg: r.el.betyg.value,
        })),
      }),
    });
    for (const utfall of data.resultat) {
      const rad = tillstand.rader.find((r) => r.anvandarnamn === utfall.anvandarnamn);
      if (rad) visaStatus(rad, utfall.status, utfall.meddelande);
    }
    const { registrerade, hinder } = data.sammanfattning;
    if (hinder === 0) {
      visaMeddelande(`${registrerade} resultat registrerades i Ladok.`, "ok");
    } else {
      visaMeddelande(`${registrerade} registrerades i Ladok, ${hinder} stoppades av hinder. Åtgärda och registrera igen.`, "varning");
    }
  } catch (fel) {
    visaMeddelande(fel.message, "fel");
  } finally {
    upptagen(knapp, false);
    uppdateraAntal();
  }
}

// ------------------------------------------------------------------ koppla ihop
$("sokformular").addEventListener("submit", hamtaUnderlag);
$("kurskod").addEventListener("change", laddaUppgiftsforslag);
$("registrera").addEventListener("click", registrera);
$("visa-pnr").addEventListener("change", uppdateraPersonnummer);
$("datum").addEventListener("change", () => {
  for (const rad of tillstand.rader) if (!rad.registrerad && !rad.el.datum.disabled) rad.el.datum.value = $("datum").value;
});
$("markera-alla").addEventListener("change", (e) => {
  for (const rad of tillstand.rader) if (!rad.el.valj.disabled) rad.el.valj.checked = e.target.checked;
  uppdateraAntal();
});

laddaUppgiftsforslag();
