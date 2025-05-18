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
use Infection\Mutator\MutatorCategory;

final class FilterBypassMutator implements Mutator
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
                $payloads = [
                    'www.whitelisted.com.evil.com',
                    'java%0d%0ascript%0d%0a:alert(0)',
                    'm',
                    'com',
                    'https:google.com',
                    '\/\/google.com/',
                    '=google。com',
                    'e%E3%80%82com',
                    'e%00.com',
                    '?next=whitelisted.com&next=google.com',
                    'http://www.theirsite.com@yoursite.com/',
                    'http://www.yoursite.com/http://www.theirsite.com/',
                    'http://www.yoursite.com/folder/www.folder.com',
                    'http://www.yoursite.com?http://www.theirsite.com/',
                    'http://www.yoursite.com?folder/www.folder.com',
                    'https://evil.c℀.example.com',
                    'http://a.com／X.b.com'
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

    public static function getDefinition(): Definition
    {
        return new Definition(
            <<<'TXT'
                Simulates filter bypass vulnerabilities by injecting various payloads to bypass domain, keyword, or character blacklists.
                TXT,
            MutatorCategory::ORTHOGONAL_REPLACEMENT,
            null,
            <<<'DIFF'
                - header("Location: /dashboard");
                + header("www.whitelisted.com.evil.com");
                + header("java%0d%0ascript%0d%0a:alert(0)");
                + header("m");
                + header("com");
                + header("https:google.com");
                + header("\/\/google.com/");
                + header("=google。com");
                + header("e%E3%80%82com");
                + header("e%00.com");
                + header("?next=whitelisted.com&next=google.com");
                + header("http://www.theirsite.com@yoursite.com/");
                + header("http://www.yoursite.com/http://www.theirsite.com/");
                + header("http://www.yoursite.com/folder/www.folder.com");
                + header("http://www.yoursite.com?http://www.theirsite.com/");
                + header("http://www.yoursite.com?folder/www.folder.com");
                + header("https://evil.c℀.example.com");
                + header("http://a.com／X.b.com");
                DIFF
        );
    }

    public function getName(): string
    {
        return 'Custom\\FilterBypassMutator';
    }
}
