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
  imports U64-BITWISE-SMT
  imports INT
  imports BOOL

  // Exact low-word projection; retain both operands and their definedness.
  rule [project-u64-or]:
      (A |Int B) modInt 18446744073709551616 => #u64Or(A, B)
    [simplification]

  rule [project-u64-xor]:
      (A xorInt B) modInt 18446744073709551616 => #u64Xor(A, B)
    [simplification]

  // Projection may run before the general masked-OR rules below.
  // Retain both operands and the default definedness obligations.
  rule [u64-or-zero-right]:
      #u64Or(A, B) ==Int 0
        => (A modInt 18446744073709551616 ==Int 0)
           andBool (B modInt 18446744073709551616 ==Int 0)
    [simplification]

  rule [u64-or-zero-left]:
      0 ==Int #u64Or(A, B)
        => (A modInt 18446744073709551616 ==Int 0)
           andBool (B modInt 18446744073709551616 ==Int 0)
    [simplification]

  // Projection must preserve the existing masked XOR sign-bit simplification.
  rule [u64-xor-sign-bit]:
      #u64Xor(X, Y) <Int 9223372036854775808
        => ((X modInt 18446744073709551616) <Int 9223372036854775808)
           ==Bool ((Y modInt 18446744073709551616) <Int 9223372036854775808)
    [simplification]

  rule [u64-xor-sign-bit-complement]:
      9223372036854775808 <=Int #u64Xor(X, Y)
        => notBool (#u64Xor(X, Y) <Int 9223372036854775808)
    [simplification]

  // Unsigned range facts; keep default ceilings for both erased operands.
  rule [u64-xor-nonnegative]:
      #u64Xor(_X, _Y) <Int 0 => false
    [simplification]

  rule [u64-xor-upper-bound]:
      #u64Xor(_X, _Y) <Int 18446744073709551616 => true
    [simplification]

  // A 32-bit shift leaves exactly the original low32 bits in the low64 word.
  rule [project-u64-shift32]:
      (A <<Int 32) modInt 18446744073709551616
        => (A modInt 4294967296) *Int 4294967296
    [simplification]

  // The projected limbs still occupy disjoint bit ranges; retain both ceilings.
  rule [u64-pack-bounded-low32]:
      #u64Or(H *Int 4294967296, L)
        => (H modInt 4294967296) *Int 4294967296 +Int L
    requires 0 <=Int L andBool L <Int 4294967296
    [simplification]

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

  // A power-of-two modulus selects low bits, which OR cannot cancel.
  rule [masked-or-zero-right]:
      ((A |Int B) modInt M) ==Int 0
        => (A modInt M ==Int 0) andBool (B modInt M ==Int 0)
    requires 0 <Int M andBool isPowerOf2(M)
    [simplification, concrete(M)]

  rule [masked-or-zero-left]:
      0 ==Int ((A |Int B) modInt M)
        => (A modInt M ==Int 0) andBool (B modInt M ==Int 0)
    requires 0 <Int M andBool isPowerOf2(M)
    [simplification, concrete(M)]

  // The selected XOR bit is zero exactly when both operand bits agree.
  // Keep default definedness, including when the two operands coincide.
  rule [masked-xor-sign-bit]:
      ((X xorInt Y) modInt M) <Int B
        => ((X modInt M) <Int B) ==Bool ((Y modInt M) <Int B)
    requires 0 <Int B andBool isPowerOf2(B) andBool M ==Int (2 *Int B)
    [simplification, concrete(B, M)]

  // Complemented low bits cannot overlap X, including when X is negative.
  // Keep default definedness: the repeated operand may be a partial expression.
  rule [masked-complement-and-right]:
      ((X xorInt MASK) modInt M) &Int X => 0
    requires 0 <Int M andBool isPowerOf2(M) andBool MASK ==Int M -Int 1
    [simplification, concrete(MASK, M)]

  rule [masked-complement-and-left]:
      X &Int ((X xorInt MASK) modInt M) => 0
    requires 0 <Int M andBool isPowerOf2(M) andBool MASK ==Int M -Int 1
    [simplification, concrete(MASK, M)]

  // Arithmetic right shift is floor division, including negative dividends.
  rule [constant-right-shift]:
      I >>Int SHIFT => I divInt (2 ^Int SHIFT)
    requires 0 <=Int SHIFT
    [simplification, concrete(SHIFT)]

  // Shifting leaves the low bits zero, including for negative high words.
  // Keep default definedness checks for both operands and the shift width.
  rule [pack-bounded-low-word]:
      (H <<Int WIDTH) |Int L => H *Int (2 ^Int WIDTH) +Int L
    requires 0 <=Int WIDTH
     andBool 0 <=Int L andBool L <Int (2 ^Int WIDTH)
    [simplification, concrete(WIDTH)]

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

  // Reverse the integer comparison so the guarded width rules apply in either orientation.
  rule [reverse-min-width-comparison]:
      ((C -Int #minWidth(N)) modInt M) >Int B
        => notBool ((B +Int 1) >Int ((C -Int #minWidth(N)) modInt M))
    [simplification, concrete(B, C, M)]

  // In this domain, minWidth(N) lies between zero and C modInt M.
  // Keep default definedness checks, especially when a constant arm erases N.
  rule [bounded-min-width-comparison-nonpositive]:
      B >Int ((C -Int #minWidth(N)) modInt M) => false
    requires 0 <Int M
     andBool 0 <=Int N andBool N <Int (2 ^Int (C modInt M))
     andBool B <=Int 0
    [simplification, concrete(B, C, M)]

  rule [bounded-min-width-comparison-above]:
      B >Int ((C -Int #minWidth(N)) modInt M) => true
    requires 0 <Int M
     andBool 0 <=Int N andBool N <Int (2 ^Int (C modInt M))
     andBool B >Int (C modInt M)
    [simplification, concrete(B, C, M)]

  rule [bounded-min-width-comparison-threshold]:
      B >Int ((C -Int #minWidth(N)) modInt M)
        => N >=Int (2 ^Int ((C modInt M) -Int B))
    requires 0 <Int M
     andBool 0 <=Int N andBool N <Int (2 ^Int (C modInt M))
     andBool 0 <Int B andBool B <=Int (C modInt M)
    [simplification, concrete(B, C, M)]

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

  // Expose both signed cases for every actual integer width, including i128/i256.
  // Preserve the partial function's domain and default operand definedness.
  rule [signed-in-range]:
      #signed(W:IWidth, N)
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

module U64-BITWISE-SMT
  imports INT

  syntax Int ::= "#u64Or" "(" Int "," Int ")"
    [function, total, symbol(u64Or),
     smt-hook((bv2int (bvor ((_ int2bv 64) #1) ((_ int2bv 64) #2))))]

  rule [u64-or-native]:
      #u64Or(X, Y) => (X |Int Y) modInt 18446744073709551616
    [concrete]

  syntax Int ::= "#u64Xor" "(" Int "," Int ")"
    [function, total, symbol(u64Xor),
     smt-hook((bv2int (bvxor ((_ int2bv 64) #1) ((_ int2bv 64) #2))))]

  rule [u64-xor-native]:
      #u64Xor(X, Y) => (X xorInt Y) modInt 18446744073709551616
    [concrete]
endmodule
```
