# Host argument validation

Validate original Val payloads before decoding loses tag or minor bits.
Known absolute references remain accepted under Komet's existing handle abstraction.

```k
requires "../configuration.md"

module HOST-ARGUMENTS
    imports CONFIG-OPERATIONS

    // Finite ABI checks for the imports added or hardened by SDK 28 support.
    // Otherwise generic loadArgs can let mismatched calls exchange leftover arguments.
    syntax Bool ::= sdk28HostSignature(String, String, FuncType) [function, total]
    rule sdk28HostSignature(M, F, TYPE) => TYPE ==K ([ i64 .ValTypes ] -> [ i64 .ValTypes ])
      requires (M ==String "b" andBool (F ==String "_" orBool F ==String "0" orBool F ==String "k"))
        orBool (M ==String "c" andBool (F ==String "_" orBool F ==String "1"))
        orBool (M ==String "a" andBool F ==String "6")
        orBool (M ==String "l" andBool F ==String "h")
    rule sdk28HostSignature("m", "b", TYPE) => TYPE ==K ([ i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
    rule sdk28HostSignature(M, F, TYPE) => TYPE ==K ([ i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
      requires (M ==String "b" andBool F ==String "g")
        orBool (M ==String "m" andBool F ==String "c")
        orBool (M ==String "l" andBool F ==String "e")
    rule sdk28HostSignature("l", "i", TYPE) => TYPE ==K ([ i64 i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
    rule sdk28HostSignature(_, _, _) => true [owise]

    syntax Bool ::= hostTypedRef(HostVal, Int, List, List) [function, total]
    rule hostTypedRef(V, TAG, OBJS, RELS)
      => getTag(V) ==Int TAG andBool getMinor(V) ==Int 0 andBool hostKnownRef(V, OBJS, RELS)

    syntax Bool ::= hostU32(HostVal) [function, total]
    rule hostU32(V) => getTag(V) ==Int 4 andBool getMinor(V) ==Int 0

    syntax Bool ::= hostKnownRef(HostVal, List, List) [function, total]
                  | hostKnownAbsolute(HostVal, List) [function, total]
    rule hostKnownRef(V, OBJS, RELS)
      => getTag(V) ==Int getTag(RELS {{ getIndex(V) }} orDefault HostVal(2))
       andBool hostKnownAbsolute(RELS {{ getIndex(V) }} orDefault HostVal(2), OBJS)
      requires isObject(V) andBool isRelativeObjectHandle(V)
    rule hostKnownRef(V, OBJS, _) => hostKnownAbsolute(V, OBJS)
      requires isObject(V) andBool notBool isRelativeObjectHandle(V)
    rule hostKnownRef(_, _, _) => false [owise]
    rule hostKnownAbsolute(V, OBJS)
      => hostObjectTag(OBJS {{ getIndex(V) }} orDefault Void) ==Int getTag(V)
      requires isObject(V) andBool notBool isRelativeObjectHandle(V)
       andBool getIndex(V) <Int size(OBJS)
    rule hostKnownAbsolute(_, _) => false [owise]

    syntax Int ::= hostObjectTag(ScVal) [function, total]
    rule hostObjectTag(V) => getTagWithFlag(true, V)

    syntax Bool ::= hostValidVal(HostVal, List, List) [function, total]
    rule hostValidVal(V, _, _) => getBody(V) ==Int 0 requires getTag(V) <=Int 2
    rule hostValidVal(V, _, _) => getMinor(V) <=Int 9 andBool (getMinor(V) ==Int 0 orBool getMajor(V) <=Int 9)
      requires getTag(V) ==Int 3
    rule hostValidVal(V, _, _) => getMinor(V) ==Int 0 requires getTag(V) ==Int 4 orBool getTag(V) ==Int 5
    rule hostValidVal(V, _, _) => true requires 6 <=Int getTag(V) andBool getTag(V) <=Int 13
    rule hostValidVal(V, _, _) => getBody(V) <Int 18014398509481984 requires getTag(V) ==Int 14
    rule hostValidVal(V, OBJS, RELS) => getMinor(V) ==Int 0 andBool hostKnownRef(V, OBJS, RELS) requires isObject(V)
    rule hostValidVal(_, _, _) => false [owise]
endmodule
```
