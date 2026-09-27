
setExitCode(1)

;; Promote packed small inputs before using native object-only limb imports.

uploadWasm( b"test-wasm",
(module $test_wasm
  (import "i" "9" (func $obj_from_u256_pieces (param i64 i64 i64 i64) (result i64)))
  (import "i" "a" (func $u256_val_from_be_bytes (param i64) (result i64)))
  (import "i" "b" (func $u256_val_to_be_bytes   (param i64) (result i64)))
  (import "i" "c" (func $obj_to_u256_hi_hi (param i64) (result i64)))
  (import "i" "d" (func $obj_to_u256_hi_lo (param i64) (result i64)))
  (import "i" "e" (func $obj_to_u256_lo_hi (param i64) (result i64)))
  (import "i" "f" (func $obj_to_u256_lo_lo (param i64) (result i64)))
  (import "i" "n" (func $add (param i64 i64) (result i64)))
  (import "i" "o" (func $sub (param i64 i64) (result i64)))
  (import "i" "p" (func $mul (param i64 i64) (result i64)))
  (import "i" "q" (func $div (param i64 i64) (result i64)))
  (func $asObject (param i64) (result i64) (local i64)
    (if (result i64)
      (i64.eq (i64.and (local.get 0) (i64.const 255)) (i64.const 12))
      (then
        (local.set 1 (i64.shr_u (local.get 0) (i64.const 8)))
        (call $obj_from_u256_pieces
          (i64.const 0)
          (i64.const 0)
          (i64.const 0)
          (local.get 1)))
      (else (local.get 0)))
  )
  (func $roundtrip (param i64) (result i64)
    (local.set 0 (call $asObject (local.get 0)))
    (call $obj_from_u256_pieces
      (call $obj_to_u256_hi_hi (local.get 0))
      (call $obj_to_u256_hi_lo (local.get 0))
      (call $obj_to_u256_lo_hi (local.get 0))
      (call $obj_to_u256_lo_lo (local.get 0))
    )
  )
  (func $roundtripBytes (param i64) (result i64)
    (call $u256_val_from_be_bytes
      (call $u256_val_to_be_bytes (local.get 0))
    )
  )
  (func $roundtripBytesInv (param i64) (result i64)
    (call $u256_val_to_be_bytes
      (call $u256_val_from_be_bytes (local.get 0))
    )
  )
  (func $addResult (param i64 i64) (result i64) (call $add (local.get 0) (local.get 1)))
  (export "add" (func $addResult))
  (func $subResult (param i64 i64) (result i64) (call $sub (local.get 0) (local.get 1)))
  (export "sub" (func $subResult))
  (func $mulResult (param i64 i64) (result i64) (call $mul (local.get 0) (local.get 1)))
  (export "mul" (func $mulResult))
  (func $divResult (param i64 i64) (result i64) (call $div (local.get 0) (local.get 1)))
  (export "div" (func $divResult))
  (export "roundtrip" (func $roundtrip))
  (export "roundtripBytes" (func $roundtripBytes))
  (export "roundtripBytesInv" (func $roundtripBytesInv))
))

setAccount(Account(b"test-account"), 9876543210)

deployContract(
  Account(b"test-account"),
  Contract(b"test-sc"),
  b"test-wasm"
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtrip",
  ListItem(U256(0)),
  U256(0)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtrip",
  ListItem(U256(100000000)),
  U256(100000000)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtrip",
  ListItem(U256(115792089237316195423570985008687907853269984665640564039457584007913129639935)), ;; MAX U256
  U256(115792089237316195423570985008687907853269984665640564039457584007913129639935)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtripBytes",
  ListItem(U256(0)),
  U256(0)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtripBytes",
  ListItem(U256(100000000)),
  U256(100000000)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtripBytes",
  ListItem(U256(115792089237316195423570985008687907853269984665640564039457584007913129639935)), ;; MAX U256
  U256(115792089237316195423570985008687907853269984665640564039457584007913129639935)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtripBytesInv",
  ListItem(ScBytes(b"abcdefghabcdefghabcdefghabcdefgh")), ;; 32 bytes
  ScBytes(b"abcdefghabcdefghabcdefghabcdefgh")
)

;; Checked arithmetic and fixed-length decoding match SDK 28 errors.
callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "add",
  ListItem(U256(1)) ListItem(U256(2)),
  U256(3)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "add",
  ListItem(U256(2 ^Int 256 -Int 2)) ListItem(U256(1)),
  U256(2 ^Int 256 -Int 1)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "add",
  ListItem(U256(2 ^Int 256 -Int 1)) ListItem(U256(1)),
  Error(ErrObject, ArithDomain)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "sub",
  ListItem(U256(7)) ListItem(U256(2)),
  U256(5)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "sub",
  ListItem(U256(2 ^Int 256 -Int 1)) ListItem(U256(2 ^Int 256 -Int 1)),
  U256(0)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "sub",
  ListItem(U256(0)) ListItem(U256(1)),
  Error(ErrObject, ArithDomain)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "mul",
  ListItem(U256(7)) ListItem(U256(3)),
  U256(21)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "mul",
  ListItem(U256(2 ^Int 256 -Int 1)) ListItem(U256(1)),
  U256(2 ^Int 256 -Int 1)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "mul",
  ListItem(U256(2 ^Int 256 -Int 1)) ListItem(U256(0)),
  U256(0)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "mul",
  ListItem(U256(2 ^Int 256 -Int 1)) ListItem(U256(2)),
  Error(ErrObject, ArithDomain)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "div",
  ListItem(U256(7)) ListItem(U256(2)),
  U256(3)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "div",
  ListItem(U256(2 ^Int 256 -Int 1)) ListItem(U256(1)),
  U256(2 ^Int 256 -Int 1)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "div",
  ListItem(U256(0)) ListItem(U256(1)),
  U256(0)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "div",
  ListItem(U256(1)) ListItem(U256(0)),
  Error(ErrObject, ArithDomain)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtripBytesInv",
  ListItem(ScBytes(b"")),
  Error(ErrObject, UnexpectedSize)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtripBytesInv",
  ListItem(ScBytes(b"abcdefghabcdefghabcdefghabcdefg")),
  Error(ErrObject, UnexpectedSize)
)

callTx(
  Account(b"test-caller"),
  Contract(b"test-sc"),
  "roundtripBytesInv",
  ListItem(ScBytes(b"abcdefghabcdefghabcdefghabcdefghi")),
  Error(ErrObject, UnexpectedSize)
)

setExitCode(0)
