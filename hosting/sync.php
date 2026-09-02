<?php
// Even Match: sync-endpoint voor de gedeelde stand.
// Upload dit bestand via FTP; de app bewaart de stand in
// evenmatch-stand.json naast dit script. Vul in de app bij
// Stand -> Sync-URL het volledige adres van dit script in,
// inclusief de sleutel: https://jouwdomein.nl/evenmatch/sync.php?key=...
//
// Vul in, minimaal 32 tekens. Zolang dit leeg is weigert het script alles
// (503), zodat een vergeten sleutel nooit stil een open endpoint oplevert.
const SLEUTEL = '';

const MAX_MATCHES = 200;
const MAX_NAAM = 80;
const MAX_BODY = 512000;

$file = __DIR__ . '/evenmatch-stand.json';

header('Access-Control-Allow-Origin: https://evenmatch.prulwerk.nl');
header('Access-Control-Allow-Methods: GET, PUT, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Vary: Origin');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }

if (strlen(SLEUTEL) < 32) {
    http_response_code(503);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Sync staat uit: vul SLEUTEL in sync.php (minimaal 32 tekens).\n";
    exit;
}

$key = $_GET['key'] ?? '';
if (!is_string($key) || !hash_equals(SLEUTEL, $key)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Verkeerde of ontbrekende sleutel.\n";
    exit;
}

function weiger(string $reden): void {
    http_response_code(400);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Ongeldige stand: $reden\n";
    exit;
}

function geldige_naam($v): bool {
    return is_string($v)
        && strlen($v) <= MAX_NAAM
        && strpos($v, '<') === false
        && strpos($v, '>') === false;
}

if ($_SERVER['REQUEST_METHOD'] === 'PUT') {
    $body = file_get_contents('php://input');
    if (strlen($body) > MAX_BODY) weiger('te groot');
    $doc = json_decode($body, true);
    if (json_last_error() !== JSON_ERROR_NONE || !is_array($doc)) weiger('geen JSON-object');
    if (!isset($doc['matches']) || !is_array($doc['matches'])) weiger('matches ontbreekt');
    if ($doc['matches'] !== array_values($doc['matches'])) weiger('matches is geen lijst');
    if (count($doc['matches']) > MAX_MATCHES) weiger('meer dan ' . MAX_MATCHES . ' matches');
    foreach ($doc['matches'] as $i => $m) {
        if (!is_array($m)) weiger("match $i is geen object");
        foreach (['sa', 'sb', 'ts'] as $veld) {
            if (!isset($m[$veld]) || !is_numeric($m[$veld])) weiger("match $i: $veld geen getal");
        }
        foreach (['an', 'bn'] as $veld) {
            if (!isset($m[$veld]) || !geldige_naam($m[$veld])) weiger("match $i: $veld ongeldig");
        }
    }
    if (isset($doc['duos'])) {
        if (!is_array($doc['duos'])) weiger('duos is geen object');
        foreach ($doc['duos'] as $v) {
            if (!geldige_naam($v)) weiger('duo-naam ongeldig');
        }
    }
    file_put_contents($file, $body, LOCK_EX);
    http_response_code(204);
    exit;
}

header('Content-Type: application/json');
echo file_exists($file) ? file_get_contents($file) : '{"matches":[]}';
