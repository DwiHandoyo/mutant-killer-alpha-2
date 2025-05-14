<?php
echo basename(dirname(__FILE__));
$targetDir = $argv[1] ?? 'src';         // Folder kode yang akan dianalisis
$outputDir = 'ast-output';              // Folder output AST
$repoBaseDir = $argv[2] ?? dirname($targetDir); // Basis direktori repo (harus berisi vendor/)

$autoloadPath = dirname(__FILE__).'/'.'vendor/autoload.php';
if (!file_exists($autoloadPath)) {
    fwrite(STDERR, "Autoload file not found at $autoloadPath\n");
    exit(1);
}

require dirname(__FILE__).'/'.'vendor/autoload.php';

use PhpParser\ParserFactory;

function getPhpFiles($dir) {
    $rii = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir));
    $files = [];
    foreach ($rii as $file) {
        if ($file->isFile() && $file->getExtension() === 'php') {
            $files[] = $file->getPathname();
        }
    }
    return $files;
}

//print parser factory
var_dump(new ParserFactory);

$parser = (new ParserFactory())->createForNewestSupportedVersion();



$files = getPhpFiles($targetDir);

echo "Found " . count($files) . " PHP files\n";

foreach ($files as $filePath) {
    $code = file_get_contents($filePath);
    $relativePath = ltrim(str_replace(getcwd(), '', $filePath), DIRECTORY_SEPARATOR);
    $jsonPath = $outputDir . '/' . $relativePath . '.json';

    try {
        $ast = $parser->parse($code);

        $jsonData = json_encode($ast, JSON_PRETTY_PRINT);

        $jsonDir = dirname($jsonPath);
        if (!is_dir($jsonDir)) {
            mkdir($jsonDir, 0777, true);
        }

        file_put_contents($jsonPath, $jsonData);

        echo "✔ Parsed: $relativePath -> $jsonPath\n";
    } catch (Exception $e) {
        echo "✘ Failed to parse $relativePath: " . $e->getMessage() . "\n";
    }
}
