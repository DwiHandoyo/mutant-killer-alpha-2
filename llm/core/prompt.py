PROMPT = """Buatkan test case PHPUnit untuk file PHP berikut. Fokus pada pengujian fungsi dan kerentanan File Inclusion. Berikan hasil tanpa penjelasan dan hanya berbentuk code php saja. Silahkan mengacu pada contoh dibawah yaitu CalculatorTest.php dimana code yang di uji terletak pada App/<nama_file>.php
<?php

namespace Tests;

use PHPUnit\Framework\TestCase;
use App\Calculator;

class CalculatorTest extends TestCase
{
    public function testAdd()
    {
        $calculator = new Calculator();
        $this->assertEquals(5, $calculator->add(2, 3));
    }

    public function testAddWithNegativeNumbers()
    {
        $calculator = new Calculator();
        $this->assertEquals(-1, $calculator->add(2, -3));
    }

    public function testAddWithZero()
    {
        $calculator = new Calculator();
        $this->assertEquals(2, $calculator->add(2, 0));
    }
}
"""

def get_prompt():
    return PROMPT