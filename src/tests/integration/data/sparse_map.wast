;; Protocol-28 sparse maps: values, raw-byte queries, validation and memory bounds.
;; Existing Komet imports expose absolute handles. Known absolute handles remain
;; accepted; forged known absolute payload isolation is outside this model.
setExitCode(1)
uploadWasm(b"sparse-map-wasm", (module
  (import "m" "b" (func $new (param i64 i64 i64) (result i64)))
  (import "m" "c" (func $unpack (param i64 i64 i64 i64) (result i64)))
  (import "v" "g" (func $vec (param i64 i64) (result i64)))
  (memory (export "memory") 1)
  (export "new" (func $new))
  (export "unpack_only" (func $unpack))
  (func (export "unpack") (param $map i64) (param $keys i64) (param $out i64) (param $len i64) (result i64)
    (drop (call $unpack (local.get $map) (local.get $keys) (local.get $out) (local.get $len)))
    (call $vec (local.get $out) (local.get $len)))
  (func (export "new_object") (param $value i64) (result i64)
    (i64.store (i32.const 256) (local.get $value))
    (call $new (i64.const 4) (i64.const 1099511627780) (i64.const 4294967300)))
  (func (export "new_mistag") (param $value i64) (result i64)
    (i64.store (i32.const 256) (i64.xor (local.get $value) (i64.const 1)))
    (call $new (i64.const 4) (i64.const 1099511627780) (i64.const 4294967300)))
  (func (export "fresh_handles") (param $map i64) (result i64)
    (drop (call $unpack (local.get $map) (i64.const 4) (i64.const 2199023255556) (i64.const 12884901892)))
    (i64.extend_i32_u (i32.and
      (i64.ne (i64.load (i32.const 512)) (i64.load (i32.const 528)))
      (i64.eqz (i64.and
        (i64.or (i64.load (i32.const 512)) (i64.load (i32.const 528)))
        (i64.const 4294967296))))))
  (data (i32.const 0) "\00\04\00\00\01\00\00\00\01\04\00\00\01\00\00\00\02\04\00\00\01\00\00\00")
  (data (i32.const 24) "\00\04\00\00\01\00\00\00\00\04\00\00\01\00\00\00")
  (data (i32.const 40) "\01\04\00\00\01\00\00\00\00\04\00\00\01\00\00\00")
  (data (i32.const 56) "\03\04\00\00\01\00\00\00")
  (data (i32.const 64) "\04\04\00\00\01\00\00\00")
  (data (i32.const 72) "\10\04\00\00\21\00\00\00")
  (data (i32.const 80) "\00\00\01\00\00\00\00\00")
  (data (i32.const 88) "\01\00\01\00\00\00\00\00")
  (data (i32.const 96) "\ff\ff\ff\ff\01\00\00\00")
  (data (i32.const 104) "\00\00\01\00\01\00\00\00")
  (data (i32.const 128) "\00\04\00\00\01\00\00\00\01\04\00\00\01\00\00\00\02\04\00\00\01\00\00\00\05\04\00\00\01\00\00\00")
  (data (i32.const 160) "\03\04\00\00\01\00\00\00\10\04\00\00\21\00\00\00")
  (data (i32.const 176) "\04\04\00\00\01\00\00\00")
  (data (i32.const 256) "\04\00\00\00\0a\00\00\00\02\00\00\00\00\00\00\00\04\00\00\00\1e\00\00\00")
  (data (i32.const 280) "\02\00\00\00\00\00\00\00\02\00\00\00\00\00\00\00\02\00\00\00\00\00\00\00")
  (data (i32.const 304) "\02\01\00\00\00\00\00\00")
  (data (i32.const 312) "\ff\00\00\00\00\00\00\00")
  (data (i32.const 320) "\48\00\00\00\64\00\00\00")
  (data (i32.const 328) "\4c\00\00\00\00\00\00\00")
  (data (i32.const 336) "\0e\00\00\00\00\00\00\40")
  (data (i32.const 344) "\03\01\00\00\0b\00\00\00")
  (data (i32.const 1024) "\61\62\63\21\ff\7a")
  (data (i32.const 1040) "\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61\61")
))
setAccount(Account(b"sparse-map-account"), 1000000000)
deployContract(Account(b"sparse-map-account"), Contract(b"sparse-map-contract"), b"sparse-map-wasm")

;; Creation filters only Void, retaining keys and values.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(256)) ListItem(U32(3)),
  ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("c")) |-> U32(30)))

;; All Void values produce empty map.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(280)) ListItem(U32(3)),
  ScMap(.Map))

;; Zero count ignores keys pointer; destination boundary is valid.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(4294967295)) ListItem(U32(65536)) ListItem(U32(0)),
  ScMap(.Map))

;; Zero values still validate the values pointer.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(4294967295)) ListItem(U32(65537)) ListItem(U32(0)),
  Error(ErrWasmVm, 1))

;; Duplicate Void rows rejected before filtering.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(24)) ListItem(U32(280)) ListItem(U32(2)),
  Error(ErrObject, 2))

;; Unsorted Void rows rejected before filtering.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(40)) ListItem(U32(280)) ListItem(U32(2)),
  Error(ErrObject, 2))

;; Invalid symbol rejected even for Void row.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(56)) ListItem(U32(280)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Invalid UTF-8 creation key rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(64)) ListItem(U32(280)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; 33-byte symbol rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(72)) ListItem(U32(280)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Key validation precedes values bounds validation.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(56)) ListItem(U32(65537)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Empty Symbol at memory end is valid.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(80)) ListItem(U32(256)) ListItem(U32(1)),
  ScMap(Symbol(str("")) |-> U32(10)))

;; Empty key slice beyond memory is invalid.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(88)) ListItem(U32(256)) ListItem(U32(1)),
  Error(ErrWasmVm, 1))

;; Key pointer plus length overflows u32.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(96)) ListItem(U32(256)) ListItem(U32(1)),
  Error(ErrValue, 0))

;; Nonempty key slice starting at memory end is invalid.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(104)) ListItem(U32(256)) ListItem(U32(1)),
  Error(ErrWasmVm, 1))

;; Descriptor must fit in memory.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(65533)) ListItem(U32(256)) ListItem(U32(1)),
  Error(ErrWasmVm, 1))

;; Values must fit in memory.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(65533)) ListItem(U32(1)),
  Error(ErrWasmVm, 1))

;; Values pointer plus bytes overflows u32.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(4294967295)) ListItem(U32(1)),
  Error(ErrValue, 0))

;; Nonzero Void body rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(304)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Reserved Val tag rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(312)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Unknown relative object rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(320)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Mistagged relative object rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(328)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Invalid SymbolSmall body rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(336)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Invalid non-contract error code rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(U32(0)) ListItem(U32(344)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Wrong argument type rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new",
  ListItem(Void) ListItem(U32(256)) ListItem(U32(1)),
  Error(ErrValue, 2))

;; Relative object value resolves into the map.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new_object",
  ListItem(ScBytes(b"object")),
  ScMap(Symbol(str("a")) |-> ScBytes(b"object")))

;; Existing relative object with wrong tag rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "new_mistag",
  ListItem(ScBytes(b"object")),
  Error(ErrValue, 2))

;; Missing and explicitly Void values both emit Void.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(128)) ListItem(U32(512)) ListItem(U32(4)),
  ScVec(ListItem(U32(10)) ListItem(Void) ListItem(U32(30)) ListItem(Void)))

;; Subset query need not exhaust map.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(8)) ListItem(U32(512)) ListItem(U32(1)),
  ScVec(ListItem(Void)))

;; Empty query ignores key pointer and still checks map.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(4294967295)) ListItem(U32(512)) ListItem(U32(0)),
  ScVec(.List))

;; Query strings need not be convertible to Symbols.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(160)) ListItem(U32(512)) ListItem(U32(2)),
  ScVec(ListItem(Void) ListItem(Void)))

;; Invalid UTF-8 query bytes are legal and absent.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(176)) ListItem(U32(512)) ListItem(U32(1)),
  ScVec(ListItem(Void)))

;; Duplicate queries rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(24)) ListItem(U32(512)) ListItem(U32(2)),
  Error(ErrObject, 2))

;; Descending queries rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(40)) ListItem(U32(512)) ListItem(U32(2)),
  Error(ErrObject, 2))

;; Output may overlap query descriptors.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(128)) ListItem(U32(128)) ListItem(U32(4)),
  ScVec(ListItem(U32(10)) ListItem(Void) ListItem(U32(30)) ListItem(Void)))

;; Empty map fills every output slot with Void.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(.Map)) ListItem(U32(128)) ListItem(U32(512)) ListItem(U32(4)),
  ScVec(ListItem(Void) ListItem(Void) ListItem(Void) ListItem(Void)))

;; Map keys must be Symbols.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(U32(1) |-> U32(2))) ListItem(U32(0)) ListItem(U32(512)) ListItem(U32(1)),
  Error(ErrValue, 8))

;; Empty query still rejects non-Symbol map key.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(ScVec(.List) |-> U32(2))) ListItem(U32(0)) ListItem(U32(512)) ListItem(U32(0)),
  Error(ErrValue, 8))

;; Trailing unqueried map keys must be Symbols.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(1) ScVec(.List) |-> U32(2))) ListItem(U32(0)) ListItem(U32(512)) ListItem(U32(1)),
  Error(ErrValue, 8))

;; Unpack descriptor bounds.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(65533)) ListItem(U32(512)) ListItem(U32(1)),
  Error(ErrWasmVm, 1))

;; Unpack empty slice bounds.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(88)) ListItem(U32(512)) ListItem(U32(1)),
  Error(ErrWasmVm, 1))

;; Unpack slice arithmetic overflow.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(96)) ListItem(U32(512)) ListItem(U32(1)),
  Error(ErrValue, 0))

;; Unpack destination bounds.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(0)) ListItem(U32(65533)) ListItem(U32(1)),
  Error(ErrWasmVm, 1))

;; Unpack destination arithmetic overflow.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(0)) ListItem(U32(4294967295)) ListItem(U32(1)),
  Error(ErrValue, 0))

;; Empty unpack destination must fit.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(0)) ListItem(U32(65537)) ListItem(U32(0)),
  Error(ErrWasmVm, 1))

;; Empty unpack permits exact memory-end destination.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack_only",
  ListItem(ScMap(Symbol(str("a")) |-> U32(10) Symbol(str("b")) |-> Void Symbol(str("c")) |-> U32(30))) ListItem(U32(0)) ListItem(U32(65536)) ListItem(U32(0)),
  Void)

;; Non-map argument rejected.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(512)) ListItem(U32(0)),
  Error(ErrValue, 2))

;; Object outputs round trip through fresh relative handles.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "unpack",
  ListItem(ScMap(Symbol(str("a")) |-> ScBytes(b"object") Symbol(str("b")) |-> Void Symbol(str("c")) |-> ScBytes(b"object"))) ListItem(U32(0)) ListItem(U32(512)) ListItem(U32(3)),
  ScVec(ListItem(ScBytes(b"object")) ListItem(Void) ListItem(ScBytes(b"object"))))

;; Each object occurrence receives a distinct relative handle.
callTx(Account(b"caller"), Contract(b"sparse-map-contract"), "fresh_handles",
  ListItem(ScMap(Symbol(str("a")) |-> ScBytes(b"object") Symbol(str("b")) |-> Void Symbol(str("c")) |-> ScBytes(b"object"))),
  SCBool(true))


;; Host linear-memory functions require a memory exported under the name "memory".
uploadWasm(b"missing-memory", (module
  (import "m" "b" (func $new (param i64 i64 i64) (result i64)))
  (import "m" "c" (func $unpack (param i64 i64 i64 i64) (result i64)))
  (export "new" (func $new))
  (export "unpack" (func $unpack))))
deployContract(Account(b"sparse-map-account"), Contract(b"missing-memory"), b"missing-memory")
callTx(Account(b"caller"), Contract(b"missing-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"missing-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"missing-memory"), "unpack",
  ListItem(ScMap(.Map)) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
;; Memory lookup occurs even before the zero-query map-key type check.
callTx(Account(b"caller"), Contract(b"missing-memory"), "unpack",
  ListItem(ScMap(U32(1) |-> U32(2))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))

;; Host linear-memory functions require a memory exported under the name "memory".
uploadWasm(b"hidden-memory", (module
  (import "m" "b" (func $new (param i64 i64 i64) (result i64)))
  (import "m" "c" (func $unpack (param i64 i64 i64 i64) (result i64)))
  (memory 1)
  (export "new" (func $new))
  (export "unpack" (func $unpack))))
deployContract(Account(b"sparse-map-account"), Contract(b"hidden-memory"), b"hidden-memory")
callTx(Account(b"caller"), Contract(b"hidden-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"hidden-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"hidden-memory"), "unpack",
  ListItem(ScMap(.Map)) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
;; Memory lookup occurs even before the zero-query map-key type check.
callTx(Account(b"caller"), Contract(b"hidden-memory"), "unpack",
  ListItem(ScMap(U32(1) |-> U32(2))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))

;; Host linear-memory functions require a memory exported under the name "memory".
uploadWasm(b"renamed-memory", (module
  (import "m" "b" (func $new (param i64 i64 i64) (result i64)))
  (import "m" "c" (func $unpack (param i64 i64 i64 i64) (result i64)))
  (memory (export "other") 1)
  (export "new" (func $new))
  (export "unpack" (func $unpack))))
deployContract(Account(b"sparse-map-account"), Contract(b"renamed-memory"), b"renamed-memory")
callTx(Account(b"caller"), Contract(b"renamed-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"renamed-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"renamed-memory"), "unpack",
  ListItem(ScMap(.Map)) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
;; Memory lookup occurs even before the zero-query map-key type check.
callTx(Account(b"caller"), Contract(b"renamed-memory"), "unpack",
  ListItem(ScMap(U32(1) |-> U32(2))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))

;; Host linear-memory functions require a memory exported under the name "memory".
uploadWasm(b"function-memory", (module
  (import "m" "b" (func $new (param i64 i64 i64) (result i64)))
  (import "m" "c" (func $unpack (param i64 i64 i64 i64) (result i64)))
  (export "memory" (func $new))
  (export "new" (func $new))
  (export "unpack" (func $unpack))))
deployContract(Account(b"sparse-map-account"), Contract(b"function-memory"), b"function-memory")
callTx(Account(b"caller"), Contract(b"function-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"function-memory"), "new",
  ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrWasmVm, 3))
callTx(Account(b"caller"), Contract(b"function-memory"), "unpack",
  ListItem(ScMap(.Map)) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))
;; Memory lookup occurs even before the zero-query map-key type check.
callTx(Account(b"caller"), Contract(b"function-memory"), "unpack",
  ListItem(ScMap(U32(1) |-> U32(2))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, 3))

setExitCode(0)
