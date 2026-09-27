```k
requires "data.md"

module KSOROBAN-LEMMAS [symbolic]
  // KWasm 0.1.155's optional trusted lemmas include false shift/modulus and
  // memory-write identities. Keep base semantics, without those optimizations.
  imports INT-BITWISE-LEMMAS
  imports HOST-OBJECT-LEMMAS
  imports SOROBAN

  syntax InternalCmd ::= runLemma(ProofStep) | doneLemma(ProofStep)
  syntax ProofStep ::= HostVal | ScVal | Int | Bool

  rule <k> runLemma(S) => doneLemma(S) ... </k>

endmodule

module INT-BITWISE-LEMMAS [symbolic]
  imports INT
  imports BOOL

  rule C |Int S => S |Int C [simplification, concrete(C), symbolic(S)]
  rule X |Int 0 => X        [simplification]
  rule [xor-zero-right]: I xorInt 0 => I [simplification]
  rule [xor-zero-left]:  0 xorInt I => I [simplification]
  // Keep the default definedness obligation for the erased operand.
  rule _X &Int 0 => 0       [simplification]

  // A nonnegative mask selects a subset of its set bits, even for negative X.
  // Keep default definedness checks: X may itself be a partial expression.
  rule [masked-int-nonnegative]:
      0 <=Int (_X &Int MASK) => true
    requires 0 <=Int MASK
    [simplification, concrete(MASK)]

  rule [masked-int-upper-bound]:
      (_X &Int MASK) <Int BOUND => true
    requires 0 <=Int MASK andBool MASK <Int BOUND
    [simplification, concrete(MASK, BOUND)]

  rule  A &Int  B          =>  B &Int  A          [simplification, concrete(A), symbolic(B)]
  rule (A &Int  B) &Int C  =>  A &Int (B  &Int C) [simplification, concrete(B, C)]
  rule  A &Int (B  &Int C) => (A &Int  B) &Int C  [simplification, symbolic(A, B)]

  syntax Bool ::= isPowerOf2(Int)  [function, total]
  rule isPowerOf2(I:Int) => I ==Int 1 <<Int log2Int(I) requires 0 <Int I
  rule isPowerOf2(I:Int) => false                      requires I <=Int 0

  syntax Bool ::= isFullMask(Int)  [function, total]
  rule isFullMask(I:Int) => I ==Int fullMask(log2Int(I) +Int 1) requires 0 <Int I
  rule isFullMask(I:Int) => false                               requires I <=Int 0

  syntax Int ::= fullMask(Int) [function, total]
  rule fullMask(I:Int) => (1 <<Int I) -Int 1 requires 0 <Int I
  rule fullMask(I:Int) => 0                  requires I <=Int 0

  // Euclidean modulo exposes full-word masking to SMT, including negative I.
  rule [full-mask-to-modulus]:
      I &Int MASK => I modInt (MASK +Int 1) requires isFullMask(MASK)
    [simplification, concrete(MASK)]

  // Arithmetic right shift is floor division, including negative dividends.
  rule [constant-right-shift]:
      I >>Int SHIFT => I divInt (2 ^Int SHIFT)
    requires 0 <=Int SHIFT
    [simplification, concrete(SHIFT)]

  // Bounded limbs occupy disjoint bit ranges; all operands remain defined.
  rule [pack-four-u64-limbs]:
      (((A <<Int 192) |Int (B <<Int 128)) |Int (C <<Int 64)) |Int D
        => A *Int (2 ^Int 192) +Int B *Int (2 ^Int 128) +Int C *Int (2 ^Int 64) +Int D
    requires 0 <=Int A andBool A <Int (2 ^Int 64)
     andBool 0 <=Int B andBool B <Int (2 ^Int 64)
     andBool 0 <=Int C andBool C <Int (2 ^Int 64)
     andBool 0 <=Int D andBool D <Int (2 ^Int 64)
    [simplification]

endmodule

module HOST-OBJECT-LEMMAS [symbolic]
  imports HOST-OBJECT
  imports INT-BITWISE-LEMMAS

  rule [boolean-word-value]:
      #bool(B:Bool) => #if B #then 1 #else 0 #fi
    [simplification]

  rule [bitwise-mk-hostval-then-mask]:
      (_I <<Int SHIFT |Int T) &Int MASK => T &Int MASK
    requires isFullMask(MASK) andBool SHIFT >=Int log2Int(MASK +Int 1)
    [simplification, concrete(SHIFT, MASK)]

  // #getRange(_,_,8)'s result always fits in 64-bit
  rule #getRange(SB, ADDR, 8) &Int 18446744073709551615 => #getRange(SB, ADDR, 8)
    [simplification]

  rule [wrap-in-range]:
      #wrap(WIDTH, N) => N
    requires 0 <Int WIDTH
     andBool 0 <=Int N andBool N <Int (1 <<Int (8 *Int WIDTH))
    [simplification, concrete(WIDTH)]

  // Expose the two defined signed-word cases to symbolic arithmetic.
  // The total wrapper is unspecified outside this unsigned-word domain.
  rule [signed-total-in-range]:
      #signedTotal(W:IValType, N)
        => #if N <Int #pow1(W) #then N #else N -Int #pow(W) #fi
    requires 0 <=Int N andBool N <Int #pow(W)
    [simplification, concrete(W)]

  // Match definedUnsigned's mixed signed/unsigned domain, including its upper half.
  rule [unsigned-in-range]:
      #unsigned(W:IWidth, N)
        => #if N <Int 0 #then N +Int #pow(W) #else N #fi
    requires 0 -Int #pow1(W) <=Int N andBool N <Int #pow(W)
    [simplification, concrete(W)]

  rule #getRange(#setRange(_BM, ADDR, VAL,  WIDTH), ADDR', WIDTH') => #wrap(WIDTH', VAL)
    requires 0 <=Int ADDR
     andBool 0  <Int WIDTH
     andBool 0 <=Int VAL andBool VAL <Int 2 ^Int (8 *Int WIDTH)
     andBool ADDR'  ==Int ADDR
     andBool WIDTH' <=Int WIDTH
    [simplification]

  // Disjoint reads are unchanged; negative values make #setRange a no-op.
  rule [getRange-before-setRange]:
      #getRange(#setRange(BM, ADDR, _VAL, WIDTH), READ_ADDR, READ_WIDTH)
        => #getRange(BM, READ_ADDR, READ_WIDTH)
    requires 0 <=Int ADDR andBool 0 <=Int WIDTH
     andBool 0 <=Int READ_ADDR andBool 0 <=Int READ_WIDTH
     andBool READ_ADDR +Int READ_WIDTH <=Int ADDR
    [simplification]

  rule [getRange-after-setRange]:
      #getRange(#setRange(BM, ADDR, _VAL, WIDTH), READ_ADDR, READ_WIDTH)
        => #getRange(BM, READ_ADDR, READ_WIDTH)
    requires 0 <=Int ADDR andBool 0 <=Int WIDTH
     andBool 0 <=Int READ_ADDR andBool 0 <=Int READ_WIDTH
     andBool ADDR +Int WIDTH <=Int READ_ADDR
    [simplification]

endmodule
```
