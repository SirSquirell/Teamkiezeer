const test = require("node:test");
const assert = require("node:assert/strict");
const EM = require("../engine.js");

const mk = (ts, extra = {}) => ({ ts, aid: "a" + ts, bid: "b" + ts, an: "Team A", bn: "Team B",
  ar: 80, br: 79, stars: 4, delta: 1, sa: 2, sb: 1, chair: "a", ...extra });
const duos = { a: "W/M", b: "J/J" };

test("normMatches gooit kapotte elementen weg", () => {
  const slecht = [null, mk(1, { sa: "5" }), mk(2, { ts: Infinity }), mk(3, { an: "<b>" }), mk(4, { bn: "x".repeat(81) })];
  assert.deepEqual(EM.normMatches(slecht), []);
});

test("normMatch weigert een score met decimalen", () => {
  assert.deepEqual(EM.normMatches([mk(1, { sa: 1.5 })]), []);
});

test("normMatch maakt van een onbekende chair none", () => {
  assert.equal(EM.normMatches([mk(2, { chair: "x" })])[0].chair, "none");
});

test("normMatches houdt alleen bekende velden", () => {
  const [m] = EM.normMatches([mk(5, { rommel: 1 })]);
  assert.deepEqual(Object.keys(m).sort(),
    ["an", "aid", "ar", "bid", "bn", "br", "chair", "delta", "sa", "sb", "stars", "ts"].sort());
});

test("normMatches kapt op 200, nieuwste eerst", () => {
  const lijst = Array.from({ length: 250 }, (_, i) => mk(i + 1));
  const uit = EM.normMatches(lijst);
  assert.equal(uit.length, 200);
  assert.equal(uit[0].ts, 250);
});

test("normMatches ontdubbelt op ts/aid/bid", () => {
  assert.equal(EM.normMatches([mk(7), mk(7)]).length, 1);
});

test("mergeStand: twee toestellen met elk een eigen match", () => {
  const basis = [mk(1), mk(2), mk(3)];
  const l = { matches: [...basis, mk(10)], duos, deleted: [] };
  const r = { matches: [...basis, mk(11)], duos, deleted: [] };
  const m = EM.mergeStand(l, r);
  assert.equal(m.matches.length, 5);
  assert.ok(m.matches.some(x => x.ts === 10) && m.matches.some(x => x.ts === 11));
});

test("mergeStand: tombstone lokaal wint van remote", () => {
  const sleutel = EM.matchKey(mk(2));
  const m = EM.mergeStand({ matches: [], duos, deleted: [sleutel] }, { matches: [mk(1), mk(2)], duos, deleted: [] });
  assert.deepEqual(m.matches.map(x => x.ts), [1]);
  assert.deepEqual(m.deleted, [sleutel]);
});

test("mergeStand: tombstone remote wint van lokaal", () => {
  const sleutel = EM.matchKey(mk(2));
  const m = EM.mergeStand({ matches: [mk(1), mk(2)], duos, deleted: [] }, { matches: [], duos, deleted: [sleutel] });
  assert.deepEqual(m.matches.map(x => x.ts), [1]);
  assert.deepEqual(m.deleted, [sleutel]);
});

test("normDuos valt terug bij ongeldige invoer", () => {
  const fb = { a: "X1", b: "Y1" };
  assert.deepEqual(EM.normDuos({ a: "X" }, fb), fb);
  assert.deepEqual(EM.normDuos({ a: "a".repeat(15), b: "B" }, fb), fb);
  assert.deepEqual(EM.normDuos({ a: "Aa", b: "Bb" }, fb), { a: "Aa", b: "Bb" });
});

test("mergeStand is idempotent", () => {
  const x = { matches: EM.normMatches([mk(1), mk(2)]), duos, deleted: EM.normDeleted([EM.matchKey(mk(9))]) };
  assert.equal(EM.standDoc(EM.mergeStand(x, x)), EM.standDoc(x));
});

test("import na wissen brengt de stand terug (herstel)", () => {
  const stand = [mk(1), mk(2)];
  const naWissen = { matches: [], duos, deleted: stand.map(EM.matchKey) };
  const gewoon = EM.mergeStand(naWissen, { matches: stand, duos, deleted: [] });
  assert.equal(gewoon.matches.length, 0);   // sync: tombstone wint
  const herstel = EM.mergeStand(naWissen, { matches: stand, duos, deleted: [] }, { herstel: true });
  assert.equal(herstel.matches.length, 2);
  assert.deepEqual(herstel.deleted.slice().sort(), stand.map(EM.matchKey).sort());   // tombstones blijven staan
});

test("herstel laat tombstones van andere matches staan", () => {
  const weg = EM.matchKey(mk(9));
  const m = EM.mergeStand({ matches: [], duos, deleted: [weg, EM.matchKey(mk(1))] }, { matches: [mk(1)], duos, deleted: [] }, { herstel: true });
  assert.equal(m.matches.length, 1);
  assert.deepEqual(m.matches.map(x => x.sa), [mk(1).sa]);
  assert.ok(m.deleted.includes(weg));
});

test("twee toestellen: wissen op A, pull op B, import op A, pull op B en A houdt de stand", () => {
  const stand = [mk(1000), mk(2000)];
  const A0 = { matches: stand, duos, deleted: [] };
  // A wist en pusht
  let A = { matches: [], duos, deleted: stand.map(EM.matchKey) };
  let server = { ...A };
  // B (had de stand) pullt en krijgt de tombstones
  let B = EM.mergeStand({ matches: stand, duos, deleted: [] }, server);
  assert.equal(B.matches.length, 0);
  // A importeert de back-up (herstel) en pusht
  A = EM.mergeStand(A, A0, { herstel: true });
  assert.equal(A.matches.length, 2);
  server = A;
  // B pullt gewoon
  B = EM.mergeStand(B, server);
  assert.equal(B.matches.length, 2);
  // A pullt wat B terugstuurt
  A = EM.mergeStand(A, B);
  assert.equal(A.matches.length, 2);
  assert.equal(EM.standDoc(A), EM.standDoc(B));
  // opnieuw importeren is idempotent
  const dubbel = EM.mergeStand(A, A0, { herstel: true });
  assert.equal(dubbel.matches.length, 2);
});

test("normDeleted: niet-numerieke sleutels geven een stabiele volgorde", () => {
  const a = EM.normDeleted(["x", "5|a|b", "y", "9|a|b"]);
  const b = EM.normDeleted(["y", "9|a|b", "x", "5|a|b"]);
  assert.deepEqual(a.slice(0, 2), ["9|a|b", "5|a|b"]);
  assert.deepEqual(a.slice().sort(), b.slice().sort());
});

test("tombstones: Alles wissen op een volle lijst verliest er geen", () => {
  const stand = Array.from({ length: EM.MAX_MATCHES }, (_, i) => mk(i + 1));
  const sleutels = stand.map(EM.matchKey);
  const nog = EM.normDeleted([...sleutels, EM.matchKey(mk(999))]);
  assert.equal(nog.length, EM.MAX_MATCHES + 1);
  assert.ok(nog.includes(sleutels[0]));
});

test("normDeleted: houdt de nieuwste 2000, ontdubbelt, gooit rommel weg", () => {
  const sleutels = Array.from({ length: 2050 }, (_, i) => `${i + 1}|a|b`);
  const uit = EM.normDeleted([...sleutels, sleutels[0], 5, null, "x".repeat(65)]);
  assert.equal(uit.length, 2000);
  assert.equal(uit[0], "2050|a|b");
  assert.equal(uit[1999], "51|a|b");
  assert.equal(new Set(uit).size, 2000);
});

test("pull zonder verschil geeft gelijke standDoc (geen push)", () => {
  const remote = { matches: EM.normMatches([mk(1), mk(2)]), duos, deleted: [] };
  const merged = EM.mergeStand({ matches: [mk(2), mk(1)], duos, deleted: [] }, remote);
  assert.equal(EM.standDoc(merged), EM.standDoc({ ...remote, duos: EM.normDuos(remote.duos, duos) }));
  const mist = EM.mergeStand({ matches: [mk(3), mk(1)], duos, deleted: [] }, remote);
  assert.notEqual(EM.standDoc(mist), EM.standDoc(remote));
});
