<?php

declare(strict_types=1);

namespace App\Mutator;

use PhpParser\Node;
use PhpParser\Node\Expr\FuncCall;
use PhpParser\Node\Scalar\String_;
use PhpParser\Node\Arg;
use PhpParser\Node\Name;
use Infection\Mutator\Mutator;
use Infection\Mutator\Definition;

final class ContentDispositionMutator implements Mutator
{
    public function canMutate(Node $node): bool
    {
        return $node instanceof FuncCall && $node->name instanceof Name && $node->name->toLowerString() === 'header';
    }

    public function mutate(Node $node): \Generator
    {
        /** @var FuncCall $node */
        foreach ($node->args as $arg) {
            if ($arg->value instanceof Node\Expr\BinaryOp\Concat || $arg->value instanceof String_) {
                if (strpos($arg->value instanceof String_ ? $arg->value->value : '', 'Content-Disposition:') !== false) {
                    yield new FuncCall(
                        new Name('header'),
                        [
                            new Arg(new String_('Content-Disposition: attachment; filename=../../etc/passwd'))
                        ]
                    );
                }
            }
        }
    }

    public static function getDefinition(): Definition
    {
        return new Definition(
            <<<'TXT'
                Simulates Content-Disposition header manipulation to download sensitive files from the server.
                TXT,
            MutatorCategory::ORTHOGONAL_REPLACEMENT,
            null,
            <<<'DIFF'
                - header("Content-Disposition: attachment; filename=file.pdf");
                + header("Content-Disposition: attachment; filename=../../etc/passwd");
                DIFF
        );
    }

    public function getName(): string
    {
        return self::class;
    }
}
