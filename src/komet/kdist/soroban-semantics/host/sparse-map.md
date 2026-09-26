# Sparse map linear memory operations (protocol 28)

The slice descriptors are little-endian `(u32 pointer, u32 length)` pairs.
Creation validates every Symbol before filtering Void values. Unpacking compares
raw query bytes, including non-Symbol bytes, and checks every map key's type.
Bounds and overflow errors use the host's error categories, including empty slices.

Object handles follow Komet's existing representation: imports may produce valid
absolute handles as well as relative handles. Known, correctly typed handles are
required, but a forged *known* absolute guest handle is indistinguishable from an
existing import's result. This module does not claim to model that isolation boundary.

```k
requires "map.md"
requires "arguments.md"

module HOST-SPARSE-MAP
    imports HOST-MAP
    imports HOST-ARGUMENTS

    rule [hostfun-sparse-map-new-from-linear-memory]:
        <instrs> hostCall("m", "b", [ i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => smRequireMemory
              ~> smNewKeys(getMajor(HostVal(K)), getMajor(HostVal(V)), getMajor(HostVal(N)), .List)
                 ...
        </instrs>
        <locals> 0 |-> < i64 > K 1 |-> < i64 > V 2 |-> < i64 > N </locals>
      requires hostU32(HostVal(K)) andBool hostU32(HostVal(V)) andBool hostU32(HostVal(N))

    rule [hostfun-sparse-map-new-invalid-args]:
        <instrs> hostCall("m", "b", [ i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
      [priority(60)]

    rule [hostfun-sparse-map-unpack-to-linear-memory]:
        <instrs> hostCall("m", "c", [ i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => smRequireMemory ~> loadObject(HostVal(M))
              ~> smUnpackStart(getMajor(HostVal(K)), getMajor(HostVal(V)), getMajor(HostVal(N)))
                 ...
        </instrs>
        <locals> 0 |-> < i64 > M 1 |-> < i64 > K 2 |-> < i64 > V 3 |-> < i64 > N </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires getTag(HostVal(M)) ==Int 76 andBool getMinor(HostVal(M)) ==Int 0
       andBool hostKnownRef(HostVal(M), OBJS, RELS)
       andBool hostU32(HostVal(K)) andBool hostU32(HostVal(V)) andBool hostU32(HostVal(N))

    rule [hostfun-sparse-map-unpack-invalid-args]:
        <instrs> hostCall("m", "c", [ i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
      [priority(60)]


    // Vm::get_memory requires an export named "memory", even for zero items.
    // KWasm retains export indices but erases their kinds; that inherited
    // abstraction cannot distinguish a same-index non-memory export here.
    syntax InternalInstr ::= "smRequireMemory"
    rule [sm-require-memory]:
        <instrs> smRequireMemory => .K ... </instrs>
        <contractModIdx> MOD </contractModIdx>
        <moduleInst>
          <modIdx> MOD </modIdx>
          <exports> ... NAME |-> IDX:Int ... </exports>
          <memAddrs> ... IDX |-> _ADDR ... </memAddrs>
          ...
        </moduleInst>
      requires NAME ==K #quoteUnparseWasmString("memory")

    rule [sm-require-memory-missing]:
        <instrs> smRequireMemory => #throw(ErrWasmVm, MissingValue) ... </instrs>
      [owise]

    // Descriptor offsets use host usize arithmetic; slice/value ranges use u32.
    syntax InternalInstr ::= smRead(Int, Int, Bool) | "smReadSlice"
    rule [sm-read]:
        <instrs> smRead(P, N, CHECK32) => .K ... </instrs>
        <hostStack> S => #getBytesRange(DATA, P, N) : S </hostStack>
        <contractModIdx> MOD </contractModIdx>
        <moduleInst> <modIdx> MOD </modIdx> <exports> ... NAME |-> IDX:Int ... </exports>
          <memAddrs> ... IDX |-> ADDR ... </memAddrs> ... </moduleInst>
        <memInst> <mAddr> ADDR </mAddr> <msize> SIZE </msize> <mdata> DATA </mdata> ... </memInst>
      requires NAME ==K #quoteUnparseWasmString("memory")
       andBool 0 <=Int P andBool 0 <=Int N andBool P +Int N <=Int SIZE *Int #pageSize()
       andBool (notBool CHECK32 orBool P +Int N <Int 4294967296)

    rule [sm-read-overflow]:
        <instrs> smRead(P, N, true) => #throw(ErrValue, ArithDomain) ... </instrs>
      requires P +Int N >=Int 4294967296

    rule [sm-read-oob]:
        <instrs> smRead(_, _, _) => #throw(ErrWasmVm, IndexBounds) ... </instrs>
      [owise]

    rule [sm-read-slice]:
        <instrs> smReadSlice
              => smRead(Bytes2Int(substrBytes(BS, 0, 4), LE, Unsigned),
                        Bytes2Int(substrBytes(BS, 4, 8), LE, Unsigned), true) ... </instrs>
        <hostStack> BS:Bytes : S => S </hostStack>

    syntax InternalInstr ::= smNewKeys(Int, Int, Int, List)
                           | smNewKey(Int, Int, Int, List)
                           | smNewVals(List)
                           | smTranslateVals(List, List)
                           | smNewEntriesStart(List)
                           | smNewEntries(List, List, Map, List)

    rule [sm-new-keys-done]:
        <instrs> smNewKeys(_, V, 0, KEYS) => smRead(V, 8 *Int size(KEYS), true) ~> smNewVals(KEYS) ... </instrs>

    rule [sm-new-keys]:
        <instrs> smNewKeys(P, V, N, KEYS)
              => smRead(P, 8, false) ~> smReadSlice ~> smNewKey(P +Int 8, V, N -Int 1, KEYS) ... </instrs>
      requires N >Int 0

    rule [sm-new-key]:
        <instrs> smNewKey(P, V, N, KEYS)
              => smNewKeys(P, V, N, KEYS ListItem(Symbol(Bytes2String(BS)))) ... </instrs>
        <hostStack> BS:Bytes : S => S </hostStack>
      requires lengthBytes(BS) <=Int 32 andBool smSymbolBytes(BS)

    rule [sm-new-key-invalid]:
        <instrs> smNewKey(_, _, _, _) => #throw(ErrValue, InvalidInput) ... </instrs>
        <hostStack> _:Bytes : S => S </hostStack>
      [owise]

    rule [sm-new-vals]:
        <instrs> smNewVals(KEYS) => smTranslateVals(Bytes2Vals(BS), .List) ~> smNewEntriesStart(KEYS) ... </instrs>
        <hostStack> BS:Bytes : S => S </hostStack>

    // Host first translates all references, then checks each key/value pair.
    rule [sm-translate-vals-done]:
        <instrs> smTranslateVals(.List, OUT) => .K ... </instrs>
        <hostStack> S => OUT : S </hostStack>

    rule [sm-translate-val]:
        <instrs> smTranslateVals(ListItem(V:HostVal) VS, OUT)
              => smTranslateVals(VS, OUT ListItem(smAbsolute(V, RELS))) ... </instrs>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires notBool isObject(V) orBool hostKnownRef(V, OBJS, RELS)

    rule [sm-translate-val-invalid]:
        <instrs> smTranslateVals(_, _) => #throw(ErrValue, InvalidInput) ... </instrs>
      [owise]

    rule [sm-new-entries-start]:
        <instrs> smNewEntriesStart(KEYS) => smNewEntries(KEYS, VALS, .Map, .List) ... </instrs>
        <hostStack> VALS:List : S => S </hostStack>

    rule [sm-new-entries-done]:
        <instrs> smNewEntries(.List, .List, M, _) => allocObject(ScMap(M)) ~> returnHostVal ... </instrs>

    rule [sm-new-entry]:
        <instrs> smNewEntries(ListItem(K:ScVal) KS, ListItem(V:HostVal) VS, M, PREV)
              => smNewEntries(KS, VS, smInsert(M, K, V), ListItem(K)) ... </instrs>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires smAfterSymbol(PREV, K) andBool hostValidVal(V, OBJS, RELS)

    rule [sm-new-entry-order]:
        <instrs> smNewEntries(ListItem(K:ScVal) _, _, _, PREV) => #throw(ErrObject, InvalidInput) ... </instrs>
      requires notBool smAfterSymbol(PREV, K)

    rule [sm-new-entry-invalid-val]:
        <instrs> smNewEntries(ListItem(K:ScVal) _, ListItem(V:HostVal) _, _, PREV)
              => #throw(ErrValue, InvalidInput) ... </instrs>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires smAfterSymbol(PREV, K) andBool notBool hostValidVal(V, OBJS, RELS)

    syntax Map ::= smInsert(Map, ScVal, HostVal) [function, total]
    rule smInsert(M, _, HostVal(2)) => M
    rule smInsert(M, K, V) => M [ K <- V ] [owise]

    syntax Bool ::= smAfterSymbol(List, ScVal) [function, total]
    rule smAfterSymbol(.List, _) => true
    rule smAfterSymbol(ListItem(Symbol(P)), Symbol(K)) => P <String K
    rule smAfterSymbol(_, _) => false [owise]

    syntax InternalInstr ::= smUnpackStart(Int, Int, Int)
                           | smUnpackKeys(Int, Int, Int, List, Map, List, List)
                           | smUnpackKey(Int, Int, Int, List, Map, List, List)
                           | smFind(Bytes, List, Map)
                           | smUnpackContinue(Int, Int, Int, Map, List, Bytes)
                           | smCheckMapKeys(List)
                           | smWrite(Int, List)
                           | smExportVals(List, List)
                           | smStore(Int)

    rule [sm-unpack-start]:
        <instrs> smUnpackStart(P, V, N) => smUnpackKeys(P, V, N, sortedKeys(M), M, .List, .List) ... </instrs>
        <hostStack> ScMap(M) : S => S </hostStack>

    rule [sm-unpack-keys-done]:
        <instrs> smUnpackKeys(_, V, 0, KEYS, _, OUT, _)
              => smCheckMapKeys(KEYS) ~> smWrite(V, OUT) ~> toSmall(Void) ... </instrs>

    rule [sm-unpack-keys]:
        <instrs> smUnpackKeys(P, V, N, KEYS, M, OUT, PREV)
              => smRead(P, 8, false) ~> smReadSlice
              ~> smUnpackKey(P +Int 8, V, N -Int 1, KEYS, M, OUT, PREV) ... </instrs>
      requires N >Int 0

    rule [sm-unpack-key]:
        <instrs> smUnpackKey(P, V, N, KEYS, M, OUT, PREV)
              => smFind(BS, KEYS, M) ~> smUnpackContinue(P, V, N, M, OUT, BS) ... </instrs>
        <hostStack> BS:Bytes : S => S </hostStack>
      requires smAfterBytes(PREV, BS)

    rule [sm-unpack-key-order]:
        <instrs> smUnpackKey(_, _, _, _, _, _, PREV) => #throw(ErrObject, InvalidInput) ... </instrs>
        <hostStack> BS:Bytes : S => S </hostStack>
      requires notBool smAfterBytes(PREV, BS)

    rule [sm-find-empty]:
        <instrs> smFind(_, .List, _) => .K ... </instrs>
        <hostStack> S => .List : HostVal(2) : S </hostStack>

    rule [sm-find-equal]:
        <instrs> smFind(BS, ListItem(Symbol(K)) KS, M) => .K ... </instrs>
        <hostStack> S => KS : (M {{ Symbol(K) }} orDefault HostVal(2)) : S </hostStack>
      requires String2Bytes(K) ==K BS

    rule [sm-find-less]:
        <instrs> smFind(BS, ListItem(Symbol(K)) KS, M) => smFind(BS, KS, M) ... </instrs>
      requires smBytesLess(String2Bytes(K), BS)

    rule [sm-find-greater]:
        <instrs> smFind(BS, ListItem(Symbol(K)) KS, _) => .K ... </instrs>
        <hostStack> S => (ListItem(Symbol(K)) KS) : HostVal(2) : S </hostStack>
      requires smBytesLess(BS, String2Bytes(K))

    rule [sm-find-non-symbol]:
        <instrs> smFind(_, ListItem(K:ScVal) _, _) => #throw(ErrValue, UnexpectedType) ... </instrs>
      requires notBool smIsSymbol(K)

    rule [sm-unpack-continue]:
        <instrs> smUnpackContinue(P, V, N, M, OUT, BS)
              => smUnpackKeys(P, V, N, KEYS, M, OUT ListItem(VAL), ListItem(BS)) ... </instrs>
        <hostStack> KEYS:List : VAL:HostVal : S => S </hostStack>

    rule [sm-check-map-keys-done]:
        <instrs> smCheckMapKeys(.List) => .K ... </instrs>
    rule [sm-check-map-key]:
        <instrs> smCheckMapKeys(ListItem(Symbol(_)) KS) => smCheckMapKeys(KS) ... </instrs>
    rule [sm-check-map-key-invalid]:
        <instrs> smCheckMapKeys(ListItem(K:ScVal) _) => #throw(ErrValue, UnexpectedType) ... </instrs>
      requires notBool smIsSymbol(K)

    // Validate the full destination before exporting handles or writing bytes.
    rule [sm-write]:
        <instrs> smWrite(P, VS) => smExportVals(VS, .List) ~> smStore(P) ... </instrs>
        <contractModIdx> MOD </contractModIdx>
        <moduleInst> <modIdx> MOD </modIdx> <exports> ... NAME |-> IDX:Int ... </exports>
          <memAddrs> ... IDX |-> ADDR ... </memAddrs> ... </moduleInst>
        <memInst> <mAddr> ADDR </mAddr> <msize> SIZE </msize> ... </memInst>
      requires NAME ==K #quoteUnparseWasmString("memory")
       andBool P +Int 8 *Int size(VS) <Int 4294967296
       andBool P +Int 8 *Int size(VS) <=Int SIZE *Int #pageSize()

    rule [sm-write-overflow]:
        <instrs> smWrite(P, VS) => #throw(ErrValue, ArithDomain) ... </instrs>
      requires P +Int 8 *Int size(VS) >=Int 4294967296
    rule [sm-write-oob]:
        <instrs> smWrite(_, _) => #throw(ErrWasmVm, IndexBounds) ... </instrs>
      [owise]

    rule [sm-export-vals-done]:
        <instrs> smExportVals(.List, OUT) => .K ... </instrs>
        <hostStack> S => Vals2Bytes(OUT) : S </hostStack>
    rule [sm-export-val-small]:
        <instrs> smExportVals(ListItem(V:HostVal) VS, OUT) => smExportVals(VS, OUT ListItem(V)) ... </instrs>
      requires notBool isObject(V)
    rule [sm-export-val-object]:
        <instrs> smExportVals(ListItem(V:HostVal) VS, OUT)
              => smExportVals(VS, OUT ListItem(fromHandleAndTag(indexToHandle(size(RELS), true), getTag(V)))) ... </instrs>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS => RELS ListItem(smAbsolute(V, RELS)) </relativeObjects>
      requires isObject(V) andBool hostKnownRef(V, OBJS, RELS)
    rule [sm-export-val-invalid]:
        <instrs> smExportVals(_, _) => #throw(ErrValue, InvalidInput) ... </instrs>
      [owise]

    rule [sm-store]:
        <instrs> smStore(P) => .K ... </instrs>
        <hostStack> BS:Bytes : S => S </hostStack>
        <contractModIdx> MOD </contractModIdx>
        <moduleInst> <modIdx> MOD </modIdx> <exports> ... NAME |-> IDX:Int ... </exports>
          <memAddrs> ... IDX |-> ADDR ... </memAddrs> ... </moduleInst>
        <memInst> <mAddr> ADDR </mAddr> <mdata> DATA => #setBytesRange(DATA, P, BS) </mdata> ... </memInst>
      requires NAME ==K #quoteUnparseWasmString("memory")
      [preserves-definedness]

    syntax Bool ::= smIsSymbol(ScVal) [function, total]
    rule smIsSymbol(Symbol(_)) => true
    rule smIsSymbol(_) => false [owise]

    syntax Bool ::= smSymbolBytes(Bytes) [function, total]
    rule smSymbolBytes(BS) => true requires lengthBytes(BS) ==Int 0
    rule smSymbolBytes(BS) => (smByte(BS) ==Int 95
                          orBool (48 <=Int smByte(BS) andBool smByte(BS) <=Int 57)
                          orBool (65 <=Int smByte(BS) andBool smByte(BS) <=Int 90)
                          orBool (97 <=Int smByte(BS) andBool smByte(BS) <=Int 122))
                         andBool smSymbolBytes(substrBytes(BS, 1, lengthBytes(BS)))
      requires lengthBytes(BS) >Int 0

    syntax Int ::= smByte(Bytes) [function, total]
    rule smByte(BS) => 0 requires lengthBytes(BS) ==Int 0
    rule smByte(BS) => Bytes2Int(substrBytes(BS, 0, 1), LE, Unsigned) requires lengthBytes(BS) >Int 0
    syntax Bool ::= smBytesLess(Bytes, Bytes) [function, total]
                 | smAfterBytes(List, Bytes) [function, total]
    rule smBytesLess(A, B) => lengthBytes(B) >Int 0 requires lengthBytes(A) ==Int 0
    rule smBytesLess(A, B) => false requires lengthBytes(A) >Int 0 andBool lengthBytes(B) ==Int 0
    rule smBytesLess(A, B) => smByte(A) <Int smByte(B)
                         orBool (smByte(A) ==Int smByte(B)
                         andBool smBytesLess(substrBytes(A, 1, lengthBytes(A)), substrBytes(B, 1, lengthBytes(B))))
      requires lengthBytes(A) >Int 0 andBool lengthBytes(B) >Int 0
    rule smAfterBytes(.List, _) => true
    rule smAfterBytes(ListItem(P:Bytes), B) => smBytesLess(P, B)
    rule smAfterBytes(_, _) => false [owise]

    syntax HostVal ::= smAbsolute(HostVal, List) [function, total]
    rule smAbsolute(V, RELS) => RELS {{ getIndex(V) }} orDefault V
      requires isObject(V) andBool isRelativeObjectHandle(V)
    rule smAbsolute(V, _) => V [owise]

endmodule
```
