# Cryptographic hashes

These executable definitions use K's byte and integer operations on both backends.
Keccak-256 uses the original Keccak `0x01` domain separator, not SHA3-256's `0x06`.
Lane order is `x + 5*y`; Keccak lanes are little endian, SHA-256 words big endian.
Protocol 28 imports are `c._` for SHA-256 and `c.1` for Keccak-256.

```k
requires "../configuration.md"
requires "../wasm-ops.md"
requires "arguments.md"
requires "integer.md"

module SOROBAN-CRYPTO
    imports BOOL
    imports BYTES
    imports INT
    imports LIST

    syntax Int ::= #cryptoWord(List, Int) [function]
    rule #cryptoWord(L, I) => {L[I]}:>Int

    syntax List ::= #cryptoWords(Bytes, Int, Endianness) [function]
    rule #cryptoWords(B, _, _) => .List requires lengthBytes(B) ==Int 0
    rule #cryptoWords(B, N, E)
      => ListItem(Bytes2Int(substrBytes(B, 0, N), E, Unsigned))
         #cryptoWords(substrBytes(B, N, lengthBytes(B)), N, E)
      requires lengthBytes(B) >=Int N andBool N >Int 0

    syntax Bytes ::= #cryptoBytes(List, Int, Endianness) [function]
    rule #cryptoBytes(.List, _, _) => .Bytes
    rule #cryptoBytes(ListItem(W:Int) WS, N, E) => Int2Bytes(N, W, E) +Bytes #cryptoBytes(WS, N, E)

    syntax Int ::= #rotl64(Int, Int) [function]
                 | #rotr32(Int, Int) [function]
    rule #rotl64(X, N) => ((X <<Int N) |Int (X >>Int (64 -Int N))) &Int 18446744073709551615
    rule #rotr32(X, N) => ((X >>Int N) |Int (X <<Int (32 -Int N))) &Int 4294967295
```

## Keccak-256

The 136-byte rate absorbs 17 lanes per block, followed by 24 Keccak-f[1600]
rounds (theta, rho/pi, chi, iota). The remaining eight lanes are capacity.
The final `0x80` padding bit shares the delimiter byte when only one byte remains.

```k
    syntax Bytes ::= #keccak256(Bytes) [function]
                   | #keccakPad(Bytes) [function]
    rule #keccak256(B)
      => substrBytes(#cryptoBytes(#keccakAbsorb(#keccakPad(B), #cryptoWords(Int2Bytes(200, 0, LE), 8, LE)), 8, LE), 0, 32)
    rule #keccakPad(B) => B +Bytes b"\x81" requires lengthBytes(B) %Int 136 ==Int 135
    rule #keccakPad(B)
      => B +Bytes b"\x01" +Bytes Int2Bytes(134 -Int (lengthBytes(B) %Int 136), 0, LE) +Bytes b"\x80"
      requires lengthBytes(B) %Int 136 <Int 135

    syntax List ::= #keccakAbsorb(Bytes, List) [function]
                  | #keccakXor(Bytes, List) [function]
                  | #keccakRounds(List, Int) [function]
    rule #keccakAbsorb(B, S) => S requires lengthBytes(B) ==Int 0
    rule #keccakAbsorb(B, S)
      => #keccakAbsorb(substrBytes(B, 136, lengthBytes(B)), #keccakRounds(#keccakXor(substrBytes(B, 0, 136), S), 0))
      requires lengthBytes(B) >=Int 136
    rule #keccakXor(B, S) => S requires lengthBytes(B) ==Int 0
    rule #keccakXor(B, ListItem(W:Int) WS)
      => ListItem(W xorInt Bytes2Int(substrBytes(B, 0, 8), LE, Unsigned))
         #keccakXor(substrBytes(B, 8, lengthBytes(B)), WS)
      requires lengthBytes(B) >=Int 8
    rule #keccakRounds(S, 24) => S
    rule #keccakRounds(S, R)
      => #keccakRounds(#keccakIota(#keccakChi(#keccakRhoPi(#keccakTheta(S, #keccakParity(S, 0), 0), 0), 0), R), R +Int 1)
      requires 0 <=Int R andBool R <Int 24

    syntax List ::= #keccakParity(List, Int) [function]
                  | #keccakTheta(List, List, Int) [function]
                  | #keccakRhoPi(List, Int) [function]
                  | #keccakChi(List, Int) [function]
                  | #keccakIota(List, Int) [function]
    rule #keccakParity(_, 5) => .List
    rule #keccakParity(S, X)
      => ListItem(#cryptoWord(S, X) xorInt #cryptoWord(S, X +Int 5) xorInt #cryptoWord(S, X +Int 10)
                  xorInt #cryptoWord(S, X +Int 15) xorInt #cryptoWord(S, X +Int 20))
         #keccakParity(S, X +Int 1)
      requires 0 <=Int X andBool X <Int 5
    rule #keccakTheta(_, _, 25) => .List
    rule #keccakTheta(S, C, I)
      => ListItem(#cryptoWord(S, I) xorInt #cryptoWord(C, (I +Int 4) %Int 5)
                  xorInt #rotl64(#cryptoWord(C, (I +Int 1) %Int 5), 1))
         #keccakTheta(S, C, I +Int 1)
      requires 0 <=Int I andBool I <Int 25
    rule #keccakRhoPi(_, 25) => .List
    rule #keccakRhoPi(S, I)
      => ListItem(#rotl64(#cryptoWord(S, #keccakSource(I)), #keccakRotation(#keccakSource(I))))
         #keccakRhoPi(S, I +Int 1)
      requires 0 <=Int I andBool I <Int 25
    rule #keccakChi(_, 25) => .List
    rule #keccakChi(S, I)
      => ListItem(#cryptoWord(S, I)
                  xorInt ((18446744073709551615 xorInt #cryptoWord(S, (I /Int 5) *Int 5 +Int ((I +Int 1) %Int 5)))
                          &Int #cryptoWord(S, (I /Int 5) *Int 5 +Int ((I +Int 2) %Int 5))))
         #keccakChi(S, I +Int 1)
      requires 0 <=Int I andBool I <Int 25
    rule #keccakIota(ListItem(W:Int) WS, R) => ListItem(W xorInt #keccakConstant(R)) WS

    syntax Int ::= #keccakSource(Int) [function]
                 | #keccakRotation(Int) [function]
                 | #keccakConstant(Int) [function]
    // Inverse of B[y, 2*x+3*y] = ROT(A[x,y], r[x,y]), modulo 5.
    rule #keccakSource(I) => ((I %Int 5 +Int 3 *Int (I /Int 5)) %Int 5) +Int 5 *Int (I %Int 5)
    rule #keccakRotation(I)
      => #cryptoWord(ListItem(0) ListItem(1) ListItem(62) ListItem(28) ListItem(27)
                     ListItem(36) ListItem(44) ListItem(6) ListItem(55) ListItem(20)
                     ListItem(3) ListItem(10) ListItem(43) ListItem(25) ListItem(39)
                     ListItem(41) ListItem(45) ListItem(15) ListItem(21) ListItem(8)
                     ListItem(18) ListItem(2) ListItem(61) ListItem(56) ListItem(14), I)
    rule #keccakConstant(R)
      => #cryptoWord(ListItem(1) ListItem(32898) ListItem(9223372036854808714) ListItem(9223372039002292224)
                     ListItem(32907) ListItem(2147483649) ListItem(9223372039002292353) ListItem(9223372036854808585)
                     ListItem(138) ListItem(136) ListItem(2147516425) ListItem(2147483658)
                     ListItem(2147516555) ListItem(9223372036854775947) ListItem(9223372036854808713) ListItem(9223372036854808579)
                     ListItem(9223372036854808578) ListItem(9223372036854775936) ListItem(32778) ListItem(9223372039002259466)
                     ListItem(9223372039002292353) ListItem(9223372036854808704) ListItem(2147483649) ListItem(9223372039002292232), R)
```

## SHA-256

FIPS 180-4 padding, schedule, and 64-round compression. Addition is reduced to
32 bits. `#sha256` also supplies raw digest bytes for contract-ID derivation.

```k
    syntax Bytes ::= #sha256(Bytes) [function]
    rule #sha256(B)
      => #cryptoBytes(#sha256Blocks(B +Bytes b"\x80"
                          +Bytes Int2Bytes((119 -Int (lengthBytes(B) %Int 64)) %Int 64, 0, BE)
                          +Bytes Int2Bytes(8, lengthBytes(B) *Int 8, BE),
                          ListItem(1779033703) ListItem(3144134277) ListItem(1013904242) ListItem(2773480762)
                          ListItem(1359893119) ListItem(2600822924) ListItem(528734635) ListItem(1541459225)), 4, BE)

    syntax List ::= #sha256Blocks(Bytes, List) [function]
                  | #sha256Add(List, List) [function]
                  | #sha256Compress(Bytes, List) [function]
                  | #sha256Schedule(List, Int) [function]
    rule #sha256Blocks(B, H) => H requires lengthBytes(B) ==Int 0
    rule #sha256Blocks(B, H)
      => #sha256Blocks(substrBytes(B, 64, lengthBytes(B)), #sha256Add(H, #sha256Compress(substrBytes(B, 0, 64), H)))
      requires lengthBytes(B) >=Int 64
    rule #sha256Add(.List, .List) => .List
    rule #sha256Add(ListItem(A:Int) AS, ListItem(B:Int) BS)
      => ListItem((A +Int B) &Int 4294967295) #sha256Add(AS, BS)
    rule #sha256Compress(BS, ListItem(A:Int) ListItem(B:Int) ListItem(C:Int) ListItem(D:Int)
                            ListItem(E:Int) ListItem(F:Int) ListItem(G:Int) ListItem(H:Int))
      => #sha256Round(#sha256Schedule(#cryptoWords(BS, 4, BE), 16), 0, A, B, C, D, E, F, G, H)
    rule #sha256Schedule(W, 64) => W
    rule #sha256Schedule(W, I)
      => #sha256Schedule(W ListItem((#sha256Small1(#cryptoWord(W, I -Int 2)) +Int #cryptoWord(W, I -Int 7)
                        +Int #sha256Small0(#cryptoWord(W, I -Int 15)) +Int #cryptoWord(W, I -Int 16)) &Int 4294967295), I +Int 1)
      requires 16 <=Int I andBool I <Int 64

    syntax Int ::= #sha256Small0(Int) [function]
                 | #sha256Small1(Int) [function]
                 | #sha256Big0(Int) [function]
                 | #sha256Big1(Int) [function]
    rule #sha256Small0(X) => #rotr32(X, 7) xorInt #rotr32(X, 18) xorInt (X >>Int 3)
    rule #sha256Small1(X) => #rotr32(X, 17) xorInt #rotr32(X, 19) xorInt (X >>Int 10)
    rule #sha256Big0(X) => #rotr32(X, 2) xorInt #rotr32(X, 13) xorInt #rotr32(X, 22)
    rule #sha256Big1(X) => #rotr32(X, 6) xorInt #rotr32(X, 11) xorInt #rotr32(X, 25)

    syntax List ::= #sha256Round(List, Int, Int, Int, Int, Int, Int, Int, Int, Int) [function]
                  | #sha256Step(List, Int, Int, Int, Int, Int, Int, Int, Int, Int, Int) [function]
    rule #sha256Round(_, 64, A, B, C, D, E, F, G, H)
      => ListItem(A) ListItem(B) ListItem(C) ListItem(D) ListItem(E) ListItem(F) ListItem(G) ListItem(H)
    rule #sha256Round(W, I, A, B, C, D, E, F, G, H)
      => #sha256Step(W, I, A, B, C, D, E, F, G,
                    H +Int #sha256Big1(E) +Int ((E &Int F) xorInt ((4294967295 xorInt E) &Int G))
                      +Int #sha256Constant(I) +Int #cryptoWord(W, I),
                    #sha256Big0(A) +Int ((A &Int B) xorInt (A &Int C) xorInt (B &Int C)))
      requires 0 <=Int I andBool I <Int 64
    rule #sha256Step(W, I, A, B, C, D, E, F, G, T1, T2)
      => #sha256Round(W, I +Int 1, (T1 +Int T2) &Int 4294967295, A, B, C, (D +Int T1) &Int 4294967295, E, F, G)
```

```k
    syntax Int ::= #sha256Constant(Int) [function]
    rule #sha256Constant(I)
      => #cryptoWord(ListItem(1116352408) ListItem(1899447441) ListItem(3049323471) ListItem(3921009573)
                     ListItem(961987163) ListItem(1508970993) ListItem(2453635748) ListItem(2870763221)
                     ListItem(3624381080) ListItem(310598401) ListItem(607225278) ListItem(1426881987)
                     ListItem(1925078388) ListItem(2162078206) ListItem(2614888103) ListItem(3248222580)
                     ListItem(3835390401) ListItem(4022224774) ListItem(264347078) ListItem(604807628)
                     ListItem(770255983) ListItem(1249150122) ListItem(1555081692) ListItem(1996064986)
                     ListItem(2554220882) ListItem(2821834349) ListItem(2952996808) ListItem(3210313671)
                     ListItem(3336571891) ListItem(3584528711) ListItem(113926993) ListItem(338241895)
                     ListItem(666307205) ListItem(773529912) ListItem(1294757372) ListItem(1396182291)
                     ListItem(1695183700) ListItem(1986661051) ListItem(2177026350) ListItem(2456956037)
                     ListItem(2730485921) ListItem(2820302411) ListItem(3259730800) ListItem(3345764771)
                     ListItem(3516065817) ListItem(3600352804) ListItem(4094571909) ListItem(275423344)
                     ListItem(430227734) ListItem(506948616) ListItem(659060556) ListItem(883997877)
                     ListItem(958139571) ListItem(1322822218) ListItem(1537002063) ListItem(1747873779)
                     ListItem(1955562222) ListItem(2024104815) ListItem(2227730452) ListItem(2361852424)
                     ListItem(2428436474) ListItem(2756734187) ListItem(3204031479) ListItem(3329325298), I)
endmodule

module HOST-CRYPTO
    imports CONFIG-OPERATIONS
    imports WASM-OPERATIONS
    imports SOROBAN-CRYPTO
    imports HOST-ARGUMENTS
    imports HOST-INTEGER

    rule [hostfun-crypto-load-bytes]:
        <instrs> hostCall("c", F, [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => loadArgs(1) ~> hostCallAux("c", F) ... </instrs>
        <locals> 0 |-> < i64 > V </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires (F ==String "_" orBool F ==String "1")
       andBool hostTypedRef(HostVal(V), 72, OBJS, RELS)

    rule [hostfun-crypto-invalid-bytes]:
        <instrs> hostCall("c", F, [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
        <locals> 0 |-> < i64 > V </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires (F ==String "_" orBool F ==String "1")
       andBool notBool hostTypedRef(HostVal(V), 72, OBJS, RELS)

    rule [hostCallAux-compute-hash-sha256]:
        <instrs> hostCallAux("c", "_") => allocObject(ScBytes(#sha256(B))) ~> returnHostVal ... </instrs>
        <hostStack> ScBytes(B) : S => S </hostStack>

    rule [hostCallAux-compute-hash-keccak256]:
        <instrs> hostCallAux("c", "1") => allocObject(ScBytes(#keccak256(B))) ~> returnHostVal ... </instrs>
        <hostStack> ScBytes(B) : S => S </hostStack>
endmodule
```
