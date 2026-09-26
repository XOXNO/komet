# ScVal XDR

The codec follows stellar-xdr 28: big-endian words, zero padding, present
container pointers, and strictly ordered map keys. Strings retain arbitrary
bytes, as Soroban strings do. Private decoder sentinels never enter host storage.
XDR recursion (500), host conversion recursion (100), and serialized byte length
(32 MiB) are checked. CPU and allocation metering remain outside this model.

```k
requires "integer.md"
requires "arguments.md"

module HOST-XDR
    imports HOST-INTEGER
    imports HOST-ARGUMENTS

    syntax InternalInstr ::= "serializeScVal" | deserializeScVal(XdrResult) | xdrReturnError(ScVal)

    rule [hostfun-serialize-to-bytes]:
        <instrs> hostCall("b", "_", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => loadObjectFull(HostVal(V)) ~> serializeScVal ... </instrs>
        <locals> 0 |-> < i64 > V </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires hostValidVal(HostVal(V), OBJS, RELS)

    rule [hostfun-serialize-invalid-val]:
        <instrs> hostCall("b", "_", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
        <locals> 0 |-> < i64 > V </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires notBool hostValidVal(HostVal(V), OBJS, RELS)
      [priority(60)]

    rule [hostfun-deserialize-argument]:
        <instrs> hostCall("b", "0", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => loadObject(HostVal(V)) ~> hostCallAux("b", "0") ... </instrs>
        <locals> 0 |-> < i64 > V </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires hostTypedRef(HostVal(V), 72, OBJS, RELS)

    rule [hostfun-deserialize-invalid-val]:
        <instrs> hostCall("b", "0", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
        <locals> 0 |-> < i64 > V </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires notBool hostTypedRef(HostVal(V), 72, OBJS, RELS)
      [priority(60)]

    rule [hostfun-serialize-scval]:
        <instrs> serializeScVal => allocObject(ScBytes(xdrEncode(V))) ~> returnHostVal ... </instrs>
        <hostStack> V:ScVal : S => S </hostStack>
      requires xdrHostDepth(V) <=Int 100
       andBool xdrWireDepth(V) <=Int 500
       andBool lengthBytes(xdrEncode(V)) <=Int 33554432

    rule [hostfun-serialize-depth]:
        <instrs> serializeScVal => #throw(ErrContext, ExceededLimit) ... </instrs>
        <hostStack> V:ScVal : S => S </hostStack>
      requires xdrHostDepth(V) >Int 100

    rule [hostfun-serialize-xdr-limit]:
        <instrs> serializeScVal => #throw(ErrBudget, ExceededLimit) ... </instrs>
        <hostStack> V:ScVal : S => S </hostStack>
      requires xdrHostDepth(V) <=Int 100
       andBool (xdrWireDepth(V) >Int 500 orBool lengthBytes(xdrEncode(V)) >Int 33554432)

    rule [hostfun-deserialize-from-bytes]:
        <instrs> hostCallAux("b", "0") => deserializeScVal(xdrRead(B, 500)) ... </instrs>
        <hostStack> ScBytes(B) : S => S </hostStack>

    rule [hostfun-deserialize-error]:
        <instrs> deserializeScVal(xdrFailure(T, C)) => #throw(T, C) ... </instrs>
    rule [hostfun-deserialize-trailing]:
        <instrs> deserializeScVal(xdrValue(_, B)) => #throw(ErrValue, InvalidInput) ... </instrs>
      requires lengthBytes(B) >Int 0
    rule [hostfun-deserialize-unsupported]:
        <instrs> deserializeScVal(xdrValue(V, REST:Bytes)) => #throw(ErrValue, UnexpectedType) ... </instrs>
      requires lengthBytes(REST) ==Int 0 andBool xdrHasUnsupported(V)
    rule [hostfun-deserialize-invalid]:
        <instrs> deserializeScVal(xdrValue(V, REST:Bytes)) => xdrReturnError(xdrValidate(V, 100)) ... </instrs>
      requires lengthBytes(REST) ==Int 0 andBool notBool xdrHasUnsupported(V) andBool xdrValidate(V, 100) =/=K Void
    rule <instrs> xdrReturnError(Error(T, C)) => #throw(T, C) ... </instrs>
    rule [hostfun-deserialize-value]:
        <instrs> deserializeScVal(xdrValue(V, REST:Bytes)) => allocObject(xdrMaterialize(V)) ~> returnHostVal ... </instrs>
      requires lengthBytes(REST) ==Int 0 andBool notBool xdrHasUnsupported(V) andBool xdrValidate(V, 100) ==K Void

    syntax Bytes ::= xdrEncode(ScVal) [function]
                   | xdrOpaque(Bytes) [function]
                   | xdrEncodeList(List) [function]
                   | xdrEncodeMap(Map, List) [function]
                   | xdrDrop(Bytes, Int) [function]
    syntax Int ::= xdrWord(Bytes, Int) [function]
                 | xdrPadding(Int) [function, total]

    rule xdrWord(B, O) => Bytes2Int(substrBytes(B, O, O +Int 4), BE, Unsigned)
      requires 0 <=Int O andBool O +Int 4 <=Int lengthBytes(B)
    rule xdrDrop(B, N) => substrBytes(B, N, lengthBytes(B))
      requires 0 <=Int N andBool N <=Int lengthBytes(B)
    rule xdrPadding(N) => (4 -Int (N %Int 4)) %Int 4
    rule xdrOpaque(B) => Int2Bytes(4, lengthBytes(B), BE) +Bytes B
                        +Bytes Int2Bytes(xdrPadding(lengthBytes(B)), 0, BE)
    rule xdrEncode(SCBool(false)) => Int2Bytes(8, 0, BE)
    rule xdrEncode(SCBool(true)) => Int2Bytes(4, 0, BE) +Bytes Int2Bytes(4, 1, BE)
    rule xdrEncode(Void) => Int2Bytes(4, 1, BE)
    rule xdrEncode(Error(T, C)) => Int2Bytes(4, 2, BE) +Bytes Int2Bytes(4, ErrorType2Int(T), BE) +Bytes Int2Bytes(4, C, BE)
    rule xdrEncode(U32(I)) => Int2Bytes(4, 3, BE) +Bytes Int2Bytes(4, I, BE)
    rule xdrEncode(I32(I)) => Int2Bytes(4, 4, BE) +Bytes Int2Bytes(4, I, BE)
    rule xdrEncode(U64(I)) => Int2Bytes(4, 5, BE) +Bytes Int2Bytes(8, I, BE)
    rule xdrEncode(I64(I)) => Int2Bytes(4, 6, BE) +Bytes Int2Bytes(8, I, BE)
    rule xdrEncode(ScTimepoint(I)) => Int2Bytes(4, 7, BE) +Bytes Int2Bytes(8, I, BE)
    rule xdrEncode(ScDuration(I)) => Int2Bytes(4, 8, BE) +Bytes Int2Bytes(8, I, BE)
    rule xdrEncode(U128(I)) => Int2Bytes(4, 9, BE) +Bytes Int2Bytes(16, I, BE)
    rule xdrEncode(I128(I)) => Int2Bytes(4, 10, BE) +Bytes Int2Bytes(16, I, BE)
    rule xdrEncode(U256(I)) => Int2Bytes(4, 11, BE) +Bytes Int2Bytes(32, I, BE)
    rule xdrEncode(I256(I)) => Int2Bytes(4, 12, BE) +Bytes Int2Bytes(32, I, BE)
    rule xdrEncode(ScBytes(B)) => Int2Bytes(4, 13, BE) +Bytes xdrOpaque(B)
    rule xdrEncode(ScString(S)) => Int2Bytes(4, 14, BE) +Bytes xdrOpaque(String2Bytes(S))
    rule xdrEncode(Symbol(S)) => Int2Bytes(4, 15, BE) +Bytes xdrOpaque(String2Bytes(S))
    rule xdrEncode(ScExecutableTag(S)) => Int2Bytes(4, 22, BE) +Bytes xdrOpaque(String2Bytes(S))
    rule xdrEncode(ScVec(L)) => Int2Bytes(4, 16, BE) +Bytes Int2Bytes(4, 1, BE) +Bytes Int2Bytes(4, size(L), BE) +Bytes xdrEncodeList(L)
    rule xdrEncode(ScMap(M)) => Int2Bytes(4, 17, BE) +Bytes Int2Bytes(4, 1, BE) +Bytes Int2Bytes(4, size(M), BE) +Bytes xdrEncodeMap(M, sortedKeys(M))
    rule xdrEncode(ScAddress(Account(B))) => Int2Bytes(4, 18, BE) +Bytes Int2Bytes(8, 0, BE) +Bytes B
    rule xdrEncode(ScAddress(Contract(B))) => Int2Bytes(4, 18, BE) +Bytes Int2Bytes(4, 1, BE) +Bytes B
    rule xdrEncode(ScAddress(MuxedAccount(I, B))) => Int2Bytes(4, 18, BE) +Bytes Int2Bytes(4, 2, BE) +Bytes Int2Bytes(8, I, BE) +Bytes B
    rule xdrEncodeList(.List) => .Bytes
    rule xdrEncodeList(ListItem(V:ScVal) REST) => xdrEncode(V) +Bytes xdrEncodeList(REST)
    rule xdrEncodeMap(_, .List) => .Bytes
    rule xdrEncodeMap(M, ListItem(K:ScVal) REST) => xdrEncode(K) +Bytes xdrEncode(M {{ K }} orDefault Void) +Bytes xdrEncodeMap(M, REST)

    // Markers preserve parsing of the rest of an invalid/non-Val-representable value.
    syntax ScVal ::= "XdrUnsupported" | XdrInvalid(ScVal) | XdrMap(List)
    // Complete the shared type classifiers for private decoder terms. Invalid
    // sentinels use an invalid host tag; successful results are materialized first.
    rule getTag(XdrMap(_)) => 76
    rule ScValTypeOrd(XdrMap(_)) => 17
    rule getTag(XdrUnsupported) => 255
    rule getTag(XdrInvalid(_)) => 255
    rule ScValTypeOrd(XdrUnsupported) => 23
    rule ScValTypeOrd(XdrInvalid(_)) => 24
    syntax XdrResult ::= xdrValue(ScVal, Bytes) | xdrFailure(ErrorType, Int)
    syntax XdrResult ::= xdrRead(Bytes, Int) [function]
                       | xdrReadTag(Int, Bytes, Int) [function]
                       | xdrReadOpaque(Int, Bytes, Int) [function]
                       | xdrOpaqueValue(Int, Bytes, Bytes) [function]
                       | xdrReadAddress(Bytes, Int) [function]
                       | xdrReadVec(Int, Bytes, Int, List) [function]
                       | xdrVecStep(XdrResult, Int, Int, List) [function]
                       | xdrReadMap(Int, Bytes, Int, List) [function]
                       | xdrMapKey(XdrResult, Int, Int, List) [function]
                       | xdrMapVal(XdrResult, ScVal, Int, Int, List) [function]
                       | xdrReadInstance(Bytes, Int) [function]
                       | xdrInstanceStorage(XdrResult) [function]
                       | xdrInstanceOwner(XdrResult, Int) [function]
                       | xdrInstanceTag(XdrResult, Int) [function]
    syntax ScVal ::= xdrMakeMapFrom(List, Map) [function]
    syntax Bool ::= xdrKeysOrdered(List) [function]
    syntax Int ::= xdrScalarWidth(Int) [function, total]
                 | xdrScalarDepth(Int) [function, total]

    rule xdrRead(B, D) => xdrReadTag(xdrWord(B, 0), xdrDrop(B, 4), D -Int 1)
      requires D >=Int 3 andBool lengthBytes(B) >=Int 4
    rule xdrRead(_, _) => xdrFailure(ErrContext, ExceededLimit) [owise]

    rule xdrReadTag(0, B, D) => xdrValue(SCBool(xdrWord(B, 0) ==Int 1), xdrDrop(B, 4))
      requires D >=Int 2 andBool lengthBytes(B) >=Int 4
    rule xdrReadTag(1, B, _) => xdrValue(Void, B)
    rule xdrReadTag(2, B, D) => xdrValue(Error(Int2ErrorType(xdrWord(B, 0)), xdrWord(B, 4)), xdrDrop(B, 8))
      requires D >=Int 3 andBool lengthBytes(B) >=Int 8
       andBool xdrWord(B, 0) <=Int 9
       andBool (xdrWord(B, 0) ==Int 0 orBool xdrWord(B, 4) <=Int 9)
    rule xdrReadTag(3, B, D) => xdrValue(U32(Bytes2Int(substrBytes(B, 0, 4), BE, Unsigned)), xdrDrop(B, 4))
      requires D >=Int xdrScalarDepth(3) andBool lengthBytes(B) >=Int 4
    rule xdrReadTag(4, B, D) => xdrValue(I32(Bytes2Int(substrBytes(B, 0, 4), BE, Signed)), xdrDrop(B, 4))
      requires D >=Int xdrScalarDepth(4) andBool lengthBytes(B) >=Int 4
    rule xdrReadTag(5, B, D) => xdrValue(U64(Bytes2Int(substrBytes(B, 0, 8), BE, Unsigned)), xdrDrop(B, 8))
      requires D >=Int xdrScalarDepth(5) andBool lengthBytes(B) >=Int 8
    rule xdrReadTag(6, B, D) => xdrValue(I64(Bytes2Int(substrBytes(B, 0, 8), BE, Signed)), xdrDrop(B, 8))
      requires D >=Int xdrScalarDepth(6) andBool lengthBytes(B) >=Int 8
    rule xdrReadTag(7, B, D) => xdrValue(ScTimepoint(Bytes2Int(substrBytes(B, 0, 8), BE, Unsigned)), xdrDrop(B, 8))
      requires D >=Int xdrScalarDepth(7) andBool lengthBytes(B) >=Int 8
    rule xdrReadTag(8, B, D) => xdrValue(ScDuration(Bytes2Int(substrBytes(B, 0, 8), BE, Unsigned)), xdrDrop(B, 8))
      requires D >=Int xdrScalarDepth(8) andBool lengthBytes(B) >=Int 8
    rule xdrReadTag(9, B, D) => xdrValue(U128(Bytes2Int(substrBytes(B, 0, 16), BE, Unsigned)), xdrDrop(B, 16))
      requires D >=Int xdrScalarDepth(9) andBool lengthBytes(B) >=Int 16
    rule xdrReadTag(10, B, D) => xdrValue(I128(Bytes2Int(substrBytes(B, 0, 16), BE, Signed)), xdrDrop(B, 16))
      requires D >=Int xdrScalarDepth(10) andBool lengthBytes(B) >=Int 16
    rule xdrReadTag(11, B, D) => xdrValue(U256(Bytes2Int(substrBytes(B, 0, 32), BE, Unsigned)), xdrDrop(B, 32))
      requires D >=Int xdrScalarDepth(11) andBool lengthBytes(B) >=Int 32
    rule xdrReadTag(12, B, D) => xdrValue(I256(Bytes2Int(substrBytes(B, 0, 32), BE, Signed)), xdrDrop(B, 32))
      requires D >=Int xdrScalarDepth(12) andBool lengthBytes(B) >=Int 32
    rule xdrReadTag(T, B, D) => xdrReadOpaque(T, B, D)
      requires (13 <=Int T andBool T <=Int 15) orBool T ==Int 22
    rule xdrReadTag(T, B, D) => xdrValue(XdrUnsupported, xdrDrop(B, 4))
      requires (T ==Int 16 orBool T ==Int 17) andBool D >=Int 2
       andBool lengthBytes(B) >=Int 4 andBool xdrWord(B, 0) ==Int 0
    rule xdrReadTag(16, B, D) => xdrReadVec(xdrWord(B, 4), xdrDrop(B, 8), D -Int 3, .List)
      requires D >=Int 4 andBool lengthBytes(B) >=Int 8 andBool xdrWord(B, 0) ==Int 1
    rule xdrReadTag(17, B, D) => xdrReadMap(xdrWord(B, 4), xdrDrop(B, 8), D -Int 4, .List)
      requires D >=Int 4 andBool lengthBytes(B) >=Int 8 andBool xdrWord(B, 0) ==Int 1
    rule xdrReadTag(T, B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires (T ==Int 16 orBool T ==Int 17) andBool D >=Int 2
       andBool lengthBytes(B) >=Int 4 andBool xdrWord(B, 0) ==Int 1
       andBool (D <Int 4 orBool lengthBytes(B) <Int 8)
    rule xdrReadTag(18, B, D) => xdrReadAddress(B, D)
    rule xdrReadTag(19, B, D) => xdrReadInstance(B, D)
    rule xdrReadTag(20, B, _) => xdrValue(XdrUnsupported, B)
    rule xdrReadTag(21, B, D) => xdrValue(XdrUnsupported, xdrDrop(B, 8))
      requires D >=Int 2 andBool lengthBytes(B) >=Int 8
    rule xdrReadTag(T, B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires 0 <=Int T andBool T <=Int 21
       andBool (lengthBytes(B) <Int xdrScalarWidth(T) orBool D <Int xdrScalarDepth(T))
       andBool (T =/=Int 2 orBool D <Int 3 orBool lengthBytes(B) <Int 4 orBool xdrWord(B, 0) <=Int 9)
    rule xdrReadTag(_, _, _) => xdrFailure(ErrValue, InvalidInput) [owise]

    rule xdrScalarWidth(0) => 4
    rule xdrScalarWidth(2) => 8
    rule xdrScalarWidth(3) => 4
    rule xdrScalarWidth(4) => 4
    rule xdrScalarWidth(T) => 8 requires 5 <=Int T andBool T <=Int 8
    rule xdrScalarWidth(T) => 16 requires 9 <=Int T andBool T <=Int 10
    rule xdrScalarWidth(T) => 32 requires 11 <=Int T andBool T <=Int 12
    rule xdrScalarWidth(16) => 4
    rule xdrScalarWidth(17) => 4
    rule xdrScalarWidth(21) => 8
    rule xdrScalarWidth(_) => 0 [owise]
    rule xdrScalarDepth(0) => 2
    rule xdrScalarDepth(2) => 3
    rule xdrScalarDepth(T) => 2 requires (7 <=Int T andBool T <=Int 12) orBool T ==Int 21
    rule xdrScalarDepth(T) => 1 requires 3 <=Int T andBool T <=Int 6
    rule xdrScalarDepth(T) => 2 requires T ==Int 16 orBool T ==Int 17
    rule xdrScalarDepth(_) => 0 [owise]

    rule xdrReadOpaque(T, B, D) => xdrOpaqueValue(T, substrBytes(B, 4, 4 +Int xdrWord(B, 0)), xdrDrop(B, 4 +Int xdrWord(B, 0) +Int xdrPadding(xdrWord(B, 0))))
      requires D >=Int 3 andBool lengthBytes(B) >=Int 4
       andBool (T =/=Int 15 orBool xdrWord(B, 0) <=Int 32)
       andBool 4 +Int xdrWord(B, 0) +Int xdrPadding(xdrWord(B, 0)) <=Int lengthBytes(B)
       andBool substrBytes(B, 4 +Int xdrWord(B, 0), 4 +Int xdrWord(B, 0) +Int xdrPadding(xdrWord(B, 0))) ==K Int2Bytes(xdrPadding(xdrWord(B, 0)), 0, BE)
    rule xdrReadOpaque(15, B, D) => xdrFailure(ErrValue, InvalidInput)
      requires D >=Int 3 andBool lengthBytes(B) >=Int 4 andBool xdrWord(B, 0) >Int 32
    rule xdrReadOpaque(_, B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires D <Int 3 orBool lengthBytes(B) <Int 4
    rule xdrReadOpaque(T, B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires D >=Int 3 andBool lengthBytes(B) >=Int 4
       andBool (T =/=Int 15 orBool xdrWord(B, 0) <=Int 32)
       andBool 4 +Int xdrWord(B, 0) +Int xdrPadding(xdrWord(B, 0)) >Int lengthBytes(B)
    rule xdrReadOpaque(_, _, _) => xdrFailure(ErrValue, InvalidInput) [owise]
    rule xdrOpaqueValue(13, B, REST) => xdrValue(ScBytes(B), REST)
    rule xdrOpaqueValue(14, B, REST) => xdrValue(ScString(Bytes2String(B)), REST)
    rule xdrOpaqueValue(22, B, REST) => xdrValue(ScExecutableTag(Bytes2String(B)), REST)
    rule xdrOpaqueValue(15, B, REST) => xdrValue(Symbol(Bytes2String(B)), REST)
      requires validSymbol(Bytes2String(B))
    rule xdrOpaqueValue(15, _, REST) => xdrValue(XdrInvalid(Error(ErrValue, InvalidInput)), REST) [owise]

    rule xdrReadAddress(B, D) => xdrValue(ScAddress(Account(substrBytes(B, 8, 40))), xdrDrop(B, 40))
      requires D >=Int 5 andBool lengthBytes(B) >=Int 40
       andBool xdrWord(B, 0) ==Int 0 andBool xdrWord(B, 4) ==Int 0
    rule xdrReadAddress(B, D) => xdrValue(ScAddress(Contract(substrBytes(B, 4, 36))), xdrDrop(B, 36))
      requires D >=Int 4 andBool lengthBytes(B) >=Int 36 andBool xdrWord(B, 0) ==Int 1
    rule xdrReadAddress(B, D) => xdrValue(ScAddress(MuxedAccount(Bytes2Int(substrBytes(B, 4, 12), BE, Unsigned), substrBytes(B, 12, 44))), xdrDrop(B, 44))
      requires D >=Int 4 andBool lengthBytes(B) >=Int 44 andBool xdrWord(B, 0) ==Int 2
    rule xdrReadAddress(B, D) => xdrValue(XdrInvalid(Error(ErrObject, UnexpectedType)), xdrDrop(B, 40))
      requires D >=Int 4 andBool lengthBytes(B) >=Int 40 andBool xdrWord(B, 0) ==Int 3 andBool xdrWord(B, 4) ==Int 0
    rule xdrReadAddress(B, D) => xdrValue(XdrInvalid(Error(ErrObject, UnexpectedType)), xdrDrop(B, 36))
      requires D >=Int 4 andBool lengthBytes(B) >=Int 36 andBool xdrWord(B, 0) ==Int 4
    rule xdrReadAddress(B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires D <Int 3 orBool lengthBytes(B) <Int 4
    rule xdrReadAddress(B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires D >=Int 3 andBool lengthBytes(B) >=Int 4
       andBool ((xdrWord(B, 0) ==Int 0 andBool (lengthBytes(B) <Int 8 orBool D <Int 5 orBool (xdrWord(B, 4) ==Int 0 andBool lengthBytes(B) <Int 40)))
         orBool ((xdrWord(B, 0) ==Int 1 orBool xdrWord(B, 0) ==Int 4) andBool (lengthBytes(B) <Int 36 orBool D <Int 4))
         orBool (xdrWord(B, 0) ==Int 2 andBool (lengthBytes(B) <Int 44 orBool D <Int 4))
         orBool (xdrWord(B, 0) ==Int 3 andBool (lengthBytes(B) <Int 8 orBool D <Int 4 orBool (xdrWord(B, 4) ==Int 0 andBool lengthBytes(B) <Int 40))))
    rule xdrReadAddress(_, _) => xdrFailure(ErrValue, InvalidInput) [owise]

    rule xdrReadVec(0, B, _, L) => xdrValue(ScVec(L), B)
    rule xdrReadVec(N, B, D, L) => xdrVecStep(xdrRead(B, D), N -Int 1, D, L) requires N >Int 0
    rule xdrVecStep(xdrValue(V, B), N, D, L) => xdrReadVec(N, B, D, L ListItem(V))
    rule xdrVecStep(xdrFailure(T, C), _, _, _) => xdrFailure(T, C)
    rule xdrReadMap(0, B, _, L) => xdrValue(XdrMap(L), B)
    rule xdrReadMap(N, B, D, L) => xdrMapKey(xdrRead(B, D), N -Int 1, D, L) requires N >Int 0
    rule xdrMapKey(xdrValue(K, B), N, D, L) => xdrMapVal(xdrRead(B, D), K, N, D, L)
    rule xdrMapKey(xdrFailure(T, C), _, _, _) => xdrFailure(T, C)
    rule xdrMapVal(xdrValue(V, B), K, N, D, L) => xdrReadMap(N, B, D, L ListItem(K) ListItem(V))
    rule xdrMapVal(xdrFailure(T, C), _, _, _, _) => xdrFailure(T, C)
    rule xdrMakeMapFrom(.List, M) => ScMap(M)
    rule xdrMakeMapFrom(ListItem(K:ScVal) ListItem(V:ScVal) REST, M) => xdrMakeMapFrom(REST, M [ K <- V ])
    rule xdrKeysOrdered(.List) => true
    rule xdrKeysOrdered(ListItem(_:ScVal) ListItem(_:ScVal)) => true
    rule xdrKeysOrdered(ListItem(K:ScVal) ListItem(_:ScVal) ListItem(K2:ScVal) ListItem(V2:ScVal) REST)
      => compare(K, K2) ==K Less andBool xdrKeysOrdered(ListItem(K2) ListItem(V2) REST)

    // ContractInstance is well-formed XDR but never a host Val.
    rule xdrReadInstance(B, D) => xdrInstanceStorage(xdrReadTag(17, xdrDrop(B, 36), D -Int 1))
      requires D >=Int 4 andBool lengthBytes(B) >=Int 36 andBool xdrWord(B, 0) ==Int 0
    rule xdrReadInstance(B, D) => xdrInstanceStorage(xdrReadTag(17, xdrDrop(B, 4), D -Int 1))
      requires D >=Int 4 andBool lengthBytes(B) >=Int 4 andBool xdrWord(B, 0) ==Int 1
    rule xdrReadInstance(B, D) => xdrInstanceOwner(xdrReadAddress(xdrDrop(B, 4), D -Int 3), D)
      requires D >=Int 4 andBool lengthBytes(B) >=Int 4 andBool xdrWord(B, 0) ==Int 2
    rule xdrReadInstance(B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires D <Int 4 orBool lengthBytes(B) <Int 4
    rule xdrReadInstance(B, D) => xdrFailure(ErrContext, ExceededLimit)
      requires D >=Int 4 andBool lengthBytes(B) >=Int 4 andBool xdrWord(B, 0) ==Int 0 andBool lengthBytes(B) <Int 36
    rule xdrReadInstance(_, _) => xdrFailure(ErrValue, InvalidInput) [owise]
    rule xdrInstanceOwner(xdrValue(_, B), D) => xdrInstanceTag(xdrReadOpaque(14, B, D -Int 3), D)
    rule xdrInstanceOwner(xdrFailure(T, C), _) => xdrFailure(T, C)
    rule xdrInstanceTag(xdrValue(_, B), D) => xdrInstanceStorage(xdrReadTag(17, B, D -Int 1))
    rule xdrInstanceTag(xdrFailure(T, C), _) => xdrFailure(T, C)
    rule xdrInstanceStorage(xdrValue(_, B)) => xdrValue(XdrUnsupported, B)
    rule xdrInstanceStorage(xdrFailure(T, C)) => xdrFailure(T, C)

    syntax Bool ::= xdrHasUnsupported(ScVal) [function, total]
                  | xdrListUnsupported(List) [function, total]
    syntax Int ::= xdrHostDepth(ScVal) [function, total]
                 | xdrListDepth(List) [function, total]
    rule xdrHasUnsupported(XdrUnsupported) => true
    rule xdrHasUnsupported(ScVec(L)) => xdrListUnsupported(L)
    rule xdrHasUnsupported(XdrMap(L)) => xdrListUnsupported(L)
    rule xdrHasUnsupported(_) => false [owise]
    rule xdrListUnsupported(.List) => false
    rule xdrListUnsupported(ListItem(V:ScVal) REST) => xdrHasUnsupported(V) orBool xdrListUnsupported(REST)
    rule xdrListUnsupported(ListItem(_) _) => true [owise]

    // Host conversion visits entries before checking map ordering. Preserve both
    // traversal order and depth until that stage; never normalize malformed maps.
    syntax ScVal ::= xdrValidate(ScVal, Int) [function]
                   | xdrValidateValue(ScVal, Int) [function]
                   | xdrValidateList(List, Int) [function]
                   | xdrValidateNext(ScVal, List, Int) [function]
                   | xdrValidateMap(ScVal, List) [function]
                   | xdrMaterialize(ScVal) [function]
    syntax List ::= xdrMaterializeList(List) [function]
    rule xdrValidate(_, D) => Error(ErrContext, ExceededLimit) requires D <=Int 0
    rule xdrValidate(V, D) => xdrValidateValue(V, D -Int 1) requires D >Int 0
    rule xdrValidateValue(XdrInvalid(E), _) => E
    rule xdrValidateValue(ScVec(L), D) => xdrValidateList(L, D)
    rule xdrValidateValue(XdrMap(L), D) => xdrValidateMap(xdrValidateList(L, D), L)
    rule xdrValidateValue(_, _) => Void [owise]
    rule xdrValidateList(.List, _) => Void
    rule xdrValidateList(ListItem(V:ScVal) REST, D) => xdrValidateNext(xdrValidate(V, D), REST, D)
    rule xdrValidateNext(Void, REST, D) => xdrValidateList(REST, D)
    rule xdrValidateNext(Error(T, C), _, _) => Error(T, C)
    rule xdrValidateMap(Error(T, C), _) => Error(T, C)
    rule xdrValidateMap(Void, L) => Void requires xdrKeysOrdered(xdrMaterializeList(L))
    rule xdrValidateMap(Void, L) => Error(ErrObject, InvalidInput) requires notBool xdrKeysOrdered(xdrMaterializeList(L))
    rule xdrMaterialize(ScVec(L)) => ScVec(xdrMaterializeList(L))
    rule xdrMaterialize(XdrMap(L)) => xdrMakeMapFrom(xdrMaterializeList(L), .Map)
    rule xdrMaterialize(V) => V [owise]
    rule xdrMaterializeList(.List) => .List
    rule xdrMaterializeList(ListItem(V:ScVal) REST) => ListItem(xdrMaterialize(V)) xdrMaterializeList(REST)

    syntax Int ::= xdrWireDepth(ScVal) [function, total]
                 | xdrListWireDepth(List) [function, total]
    rule xdrWireDepth(ScVec(L)) => maxInt(5, 4 +Int xdrListWireDepth(L))
    rule xdrWireDepth(ScMap(M)) => maxInt(5, 5 +Int maxInt(xdrListWireDepth(keys_list(M)), xdrListWireDepth(values(M))))
    rule xdrWireDepth(Error(_, _)) => 4
    rule xdrWireDepth(ScBytes(_)) => 4
    rule xdrWireDepth(ScString(_)) => 4
    rule xdrWireDepth(Symbol(_)) => 4
    rule xdrWireDepth(ScExecutableTag(_)) => 4
    rule xdrWireDepth(ScAddress(Account(_))) => 6
    rule xdrWireDepth(ScAddress(Contract(_))) => 5
    rule xdrWireDepth(ScAddress(MuxedAccount(_, _))) => 5
    rule xdrWireDepth(_) => 3 [owise]
    rule xdrListWireDepth(.List) => 0
    rule xdrListWireDepth(ListItem(V:ScVal) REST) => maxInt(xdrWireDepth(V), xdrListWireDepth(REST))
    rule xdrListWireDepth(ListItem(_) _) => 501 [owise]

    rule xdrHostDepth(ScVec(L)) => 1 +Int xdrListDepth(L)
    rule xdrHostDepth(ScMap(M)) => 1 +Int maxInt(xdrListDepth(keys_list(M)), xdrListDepth(values(M)))
    rule xdrHostDepth(_) => 1 [owise]
    rule xdrListDepth(.List) => 0
    rule xdrListDepth(ListItem(V:ScVal) REST) => maxInt(xdrHostDepth(V), xdrListDepth(REST))
    rule xdrListDepth(ListItem(_) _) => 101 [owise]
endmodule
```
