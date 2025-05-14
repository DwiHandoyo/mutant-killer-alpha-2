<?php
require 'vendor/autoload.php';

use PhpParser\ParserFactory;
use PhpParser\PrettyPrinter\Standard;
use PhpParser\Node;
use PhpParser\BuilderFactory;

// Ambil path dari argumen CLI
$astFile = $argv[1] ?? null;

if (!$astFile || !file_exists($astFile)) {
    fwrite(STDERR, "File AST tidak ditemukan: $astFile\n");
    exit(1);
}

// Baca JSON AST
$astJson = file_get_contents($astFile);
$astArray = json_decode($astJson, true);

if ($astArray === null) {
    fwrite(STDERR, "Gagal decode JSON\n");
    exit(1);
}

// Konversi array ke AST node
$serializer = new PhpParser\Serializer\Json;
$stmts = $serializer->decode($astArray);

// Cetak kembali ke kode PHP
$prettyPrinter = new Standard;
echo $prettyPrinter->prettyPrintFile($stmts);
