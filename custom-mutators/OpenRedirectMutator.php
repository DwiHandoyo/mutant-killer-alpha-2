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

final class OpenRedirectMutator implements Mutator
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
                if (strpos($arg->value instanceof String_ ? $arg->value->value : '', 'Location:') !== false) {
                    yield new FuncCall(
                        new Name('header'),
                        [
                            new Arg(new String_('Location: http://evil.com'))
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
                Simulates open redirect vulnerability by modifying the `Location` header to redirect to an external malicious site.
                TXT,
            MutatorCategory::ORTHOGONAL_REPLACEMENT,
            null,
            <<<'DIFF'
                - header("Location: /dashboard");
                + header("Location: http://evil.com");
                DIFF
        );
    }

    public function getName(): string
    {
        return 'Custom\\OpenRedirectMutator';
    }
}
