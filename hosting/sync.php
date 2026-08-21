<?php
// Even Match — sync-endpoint voor de gedeelde stand.
// Upload dit bestand via FTP; de app bewaart de stand in
// evenmatch-stand.json naast dit script. Vul in de app bij
// Stand → Sync-URL het volledige adres van dit script in.
$file = __DIR__ . '/evenmatch-stand.json';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, PUT, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }

if ($_SERVER['REQUEST_METHOD'] === 'PUT') {
    $body = file_get_contents('php://input');
    json_decode($body);
    if (json_last_error() !== JSON_ERROR_NONE || strlen($body) > 512000) {
        http_response_code(400);
        exit;
    }
    file_put_contents($file, $body, LOCK_EX);
    http_response_code(204);
    exit;
}

header('Content-Type: application/json');
echo file_exists($file) ? file_get_contents($file) : '{"results":[]}';
