/* engine.js: pure stand-logica (normalisatie en merge). Geen DOM, geen opslag,
   geen netwerk; app.js roept dit aan en node --test test/ test het. */
(function (root) {
"use strict";
const MAX_MATCHES = 200, MAX_NAAM = 80, MAX_DUO = 14, MAX_VERWIJDERSLEUTEL = 64, MAX_TOMBSTONES = 2000;
const CHAIRS = new Set(["a", "b", "none"]);
const str = (v, max) => typeof v === "string" && v.length <= max && !/[<>]/.test(v) ? v : null;
const numOrNull = v => typeof v === "number" && Number.isFinite(v) ? v : null;
const matchKey = m => `${m.ts}|${m.aid || ""}|${m.bid || ""}`;
function normMatch(m){
  if (!m || typeof m !== "object" || Array.isArray(m)) return null;
  const score = v => typeof v === "number" && Number.isInteger(v) && v >= 0 && v <= 99 ? v : null;
  const sa = score(m.sa), sb = score(m.sb);
  const ts = typeof m.ts === "number" && Number.isFinite(m.ts) && m.ts > 0 ? m.ts : null;
  const an = str(m.an, MAX_NAAM), bn = str(m.bn, MAX_NAAM);
  if (sa === null || sb === null || ts === null || an === null || bn === null) return null;
  return { ts, aid: typeof m.aid === "string" ? m.aid : "", bid: typeof m.bid === "string" ? m.bid : "",
           an, bn, ar: numOrNull(m.ar), br: numOrNull(m.br), stars: numOrNull(m.stars), delta: numOrNull(m.delta),
           sa, sb, chair: CHAIRS.has(m.chair) ? m.chair : "none" };
}
function normMatches(list){
  if (!Array.isArray(list)) return [];
  const seen = new Set(), out = [];
  for (const m of list.map(normMatch).filter(Boolean).sort((x, y) => y.ts - x.ts)){
    const k = matchKey(m); if (seen.has(k)) continue; seen.add(k); out.push(m);
  }
  return out.slice(0, MAX_MATCHES);
}
const sleutelTs = k => { const n = parseFloat(k); return Number.isFinite(n) ? n : 0; };
function normDeleted(list){
  if (!Array.isArray(list)) return [];
  const out = [...new Set(list.filter(k => typeof k === "string" && k.length <= MAX_VERWIJDERSLEUTEL))];
  return out.sort((x, y) => sleutelTs(y) - sleutelTs(x)).slice(0, MAX_TOMBSTONES);
}
function normDuos(d, fallback){
  const a = d && str(d.a, MAX_DUO), b = d && str(d.b, MAX_DUO);
  return a && b ? { a, b } : { a: fallback.a, b: fallback.b };
}
/* Unie op sleutel ts|aid|bid, tombstones winnen van beide kanten, duos van remote als die geldig zijn.
   Met { herstel:true } (import) krijgt een teruggezette match die een tombstone raakt een nieuwe
   identiteit: ts gaat 1 ms omhoog tot de sleutel vrij is. De tombstone blijft staan en reist mee, dus
   ook een toestel dat hem al heeft laat de teruggezette match staan. Geen klok nodig: deterministisch. */
function mergeStand(local, remote, opties){
  const deleted = normDeleted([...(local.deleted || []), ...(remote.deleted || [])]);
  const dood = new Set(deleted);
  let terug = normMatches(remote.matches || []);
  if (opties && opties.herstel){
    terug = terug.map(m => {
      if (!dood.has(matchKey(m))) return m;
      let n = { ...m };
      do { n = { ...n, ts: n.ts + 1 }; } while (dood.has(matchKey(n)));
      return n;
    });
  }
  const matches = normMatches([...(local.matches || []), ...terug]).filter(m => !dood.has(matchKey(m)));
  return { matches, duos: normDuos(remote.duos, local.duos), deleted };
}
const standDoc = s => JSON.stringify({ matches: s.matches, duos: s.duos, deleted: s.deleted });
const EM = { matchKey, normMatch, normMatches, normDeleted, normDuos, mergeStand, standDoc, MAX_MATCHES };
if (typeof module === "object" && module.exports) module.exports = EM; else root.EM = EM;
})(globalThis);
