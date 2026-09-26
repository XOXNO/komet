setExitCode(1)
uploadWasm(b"string-tests", (module
  (import "b" "k" (func $len (param i64) (result i64)))
  (import "b" "g" (func $copy (param i64 i64 i64 i64) (result i64)))
  (import "b" "3" (func $bytes (param i64 i64) (result i64)))
  (import "b" "i" (func $string (param i64 i64) (result i64)))
  (memory (export "memory") 1)
  (data (i32.const 0) "\c3\a9\ff")
  (func $minor_offset (param i64) (result i64)
    (call $copy (local.get 0) (i64.const 260) (i64.const 4) (i64.const 4)))
  (func $mistag (param i64) (result i64)
    (call $len (i64.xor (local.get 0) (i64.const 1))))
  (func $copy_result (param i64 i64 i64 i64) (result i64)
    (call $copy (local.get 0) (local.get 1) (local.get 2) (local.get 3))
    drop
    (call $bytes (local.get 2) (local.get 3)))
  (func $raw_len (result i64)
    (call $len (call $string (i64.const 4) (i64.const 12884901892))))
  (func $raw_copy (result i64)
    (call $copy_result
      (call $string (i64.const 4) (i64.const 12884901892))
      (i64.const 4294967300) (i64.const 68719476740) (i64.const 8589934596)))
  (export "len" (func $len))
  (export "copy" (func $copy_result))
  (export "minor_offset" (func $minor_offset))
  (export "mistag" (func $mistag))
  (export "raw_len" (func $raw_len))
  (export "raw_copy" (func $raw_copy))
))
deployContract(Account(b"owner"), Contract(b"strings"), b"string-tests")

callTx(Account(b"caller"), Contract(b"strings"), "len",
  ListItem(ScString(str(""))), U32(0))
callTx(Account(b"caller"), Contract(b"strings"), "raw_len", .List, U32(3))
callTx(Account(b"caller"), Contract(b"strings"), "copy",
  ListItem(ScString(str("abcd"))) ListItem(U32(1)) ListItem(U32(0)) ListItem(U32(2)), ScBytes(b"bc"))
callTx(Account(b"caller"), Contract(b"strings"), "raw_copy", .List, ScBytes(b"\xa9\xff"))
callTx(Account(b"caller"), Contract(b"strings"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(1)) ListItem(U32(65536)) ListItem(U32(0)), ScBytes(b""))
callTx(Account(b"caller"), Contract(b"strings"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(2)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrObject, IndexBounds))
callTx(Account(b"caller"), Contract(b"strings"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(4294967295)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrValue, ArithDomain))
callTx(Account(b"caller"), Contract(b"strings"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(0)) ListItem(U32(65536)) ListItem(U32(1)), Error(ErrWasmVm, IndexBounds))
callTx(Account(b"caller"), Contract(b"strings"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(0)) ListItem(U32(65537)) ListItem(U32(0)), Error(ErrWasmVm, IndexBounds))
callTx(Account(b"caller"), Contract(b"strings"), "len",
  ListItem(U32(7)), Error(ErrValue, InvalidInput))
callTx(Account(b"caller"), Contract(b"strings"), "copy",
  ListItem(ScBytes(b"a")) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrValue, InvalidInput))
callTx(Account(b"caller"), Contract(b"strings"), "minor_offset",
  ListItem(ScString(str("a"))), Error(ErrValue, InvalidInput))
callTx(Account(b"caller"), Contract(b"strings"), "mistag",
  ListItem(ScString(str("a"))), Error(ErrValue, InvalidInput))

uploadWasm(b"string-unexported", (module
  (import "b" "g" (func $copy (param i64 i64 i64 i64) (result i64)))
  (memory 1)
  (export "copy" (func $copy))
))
deployContract(Account(b"owner"), Contract(b"unexported"), b"string-unexported")
callTx(Account(b"caller"), Contract(b"unexported"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, MissingValue))
callTx(Account(b"caller"), Contract(b"unexported"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrWasmVm, MissingValue))
callTx(Account(b"caller"), Contract(b"unexported"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(2)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrObject, IndexBounds))

uploadWasm(b"string-no-memory", (module
  (import "b" "k" (func $len (param i64) (result i64)))
  (import "b" "g" (func $copy (param i64 i64 i64 i64) (result i64)))
  (export "len" (func $len))
  (export "copy" (func $copy))
))
deployContract(Account(b"owner"), Contract(b"no-memory"), b"string-no-memory")
callTx(Account(b"caller"), Contract(b"no-memory"), "len",
  ListItem(ScString(str("a"))), U32(1))
callTx(Account(b"caller"), Contract(b"no-memory"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(0)), Error(ErrWasmVm, MissingValue))
callTx(Account(b"caller"), Contract(b"no-memory"), "copy",
  ListItem(ScString(str("a"))) ListItem(U32(0)) ListItem(U32(0)) ListItem(U32(1)), Error(ErrWasmVm, MissingValue))

;; Mismatched host signatures must not exchange leftover arguments through the host stack.
uploadWasm(b"string-wrong-signatures", (module
  (import "b" "k" (func $len (param i64 i64) (result i64)))
  (import "b" "g" (func $copy (param i64 i64 i64) (result i64)))
  (memory (export "memory") 1)
  (func $run (param i64) (result i64)
    (call $len (local.get 0) (i64.const 4))
    drop
    (call $copy (local.get 0) (i64.const 4) (i64.const 4)))
  (export "run" (func $run))
))
deployContract(Account(b"owner"), Contract(b"wrong-signatures"), b"string-wrong-signatures")
callTx(Account(b"caller"), Contract(b"wrong-signatures"), "run",
  ListItem(ScString(str("a"))), Error(ErrWasmVm, InvalidAction))
setExitCode(0)
