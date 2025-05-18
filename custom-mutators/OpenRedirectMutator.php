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
                    $payloads = [
                        'Location: https://example.com/redirect/http://malicious.com',
                        'Location: https://example.com/redirect/../http://malicious.com',
                        'Location: ?checkout_url=http://malicious.com',
                        'Location: ?continue=http://malicious.com',
                        'Location: ?dest=http://malicious.com',
                        'Location: ?destination=http://malicious.com',
                        'Location: ?go=http://malicious.com',
                        'Location: ?image_url=http://malicious.com',
                        'Location: ?next=http://malicious.com',
                        'Location: ?redir=http://malicious.com',
                        'Location: ?redirect_uri=http://malicious.com',
                        'Location: ?redirect_url=http://malicious.com',
                        'Location: ?redirect=http://malicious.com',
                        'Location: ?return_path=http://malicious.com',
                        'Location: ?return_to=http://malicious.com',
                        'Location: ?return=http://malicious.com',
                        'Location: ?returnTo=http://malicious.com',
                        'Location: ?rurl=http://malicious.com',
                        'Location: ?target=http://malicious.com',
                        'Location: ?url=http://malicious.com',
                        'Location: ?view=http://malicious.com',
                        'Location: /http://malicious.com'
                    ];

                    foreach ($payloads as $payload) {
                        yield new FuncCall(
                            new Name('header'),
                            [
                                new Arg(new String_($payload))
                            ]
                        );
                    }
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
                + header("Location: https://example.com/redirect/http://malicious.com");
                + header("Location: https://example.com/redirect/../http://malicious.com");
                + header("Location: ?checkout_url=http://malicious.com");
                + header("Location: ?continue=http://malicious.com");
                + header("Location: ?dest=http://malicious.com");
                + header("Location: ?destination=http://malicious.com");
                + header("Location: ?go=http://malicious.com");
                + header("Location: ?image_url=http://malicious.com");
                + header("Location: ?next=http://malicious.com");
                + header("Location: ?redir=http://malicious.com");
                + header("Location: ?redirect_uri=http://malicious.com");
                + header("Location: ?redirect_url=http://malicious.com");
                + header("Location: ?redirect=http://malicious.com");
                + header("Location: ?return_path=http://malicious.com");
                + header("Location: ?return_to=http://malicious.com");
                + header("Location: ?return=http://malicious.com");
                + header("Location: ?returnTo=http://malicious.com");
                + header("Location: ?rurl=http://malicious.com");
                + header("Location: ?target=http://malicious.com");
                + header("Location: ?url=http://malicious.com");
                + header("Location: ?view=http://malicious.com");
                + header("Location: /http://malicious.com");
                DIFF
        );
    }

    public function getName(): string
    {
        return 'Custom\\OpenRedirectMutator';
    }
}
