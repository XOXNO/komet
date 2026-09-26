setExitCode(1)

;; Invalid raw Val inputs must throw, never load a differently tagged object.
uploadWasm(b"crypto-invalid", (module
  (import "c" "_" (func $sha (param i64) (result i64)))
  (import "c" "1" (func $keccak (param i64) (result i64)))
  (func (export "sha_hash") (param i64) (result i64) local.get 0 call $sha)
  (func (export "sha_string_tag") (param i64) (result i64) local.get 0 i64.const -256 i64.and i64.const 73 i64.or call $sha)
  (func (export "sha_bytes_tag") (param i64) (result i64) local.get 0 i64.const -256 i64.and i64.const 72 i64.or call $sha)
  (func (export "sha_minor") (param i64) (result i64) local.get 0 i64.const 256 i64.or call $sha)
  (func (export "sha_unknown_relative") (result i64) i64.const 8589934592072 call $sha)
  (func (export "sha_unknown_absolute") (result i64) i64.const 8594229559368 call $sha)
  (func (export "keccak_hash") (param i64) (result i64) local.get 0 call $keccak)
  (func (export "keccak_string_tag") (param i64) (result i64) local.get 0 i64.const -256 i64.and i64.const 73 i64.or call $keccak)
  (func (export "keccak_bytes_tag") (param i64) (result i64) local.get 0 i64.const -256 i64.and i64.const 72 i64.or call $keccak)
  (func (export "keccak_minor") (param i64) (result i64) local.get 0 i64.const 256 i64.or call $keccak)
  (func (export "keccak_unknown_relative") (result i64) i64.const 8589934592072 call $keccak)
  (func (export "keccak_unknown_absolute") (result i64) i64.const 8594229559368 call $keccak)
))
setAccount(Account(b"account"), 1000000)
deployContract(Account(b"account"), Contract(b"crypto-invalid"), b"crypto-invalid")

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_hash",
  ListItem(U32(0)), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_hash",
  ListItem(Void), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_hash",
  ListItem(ScString(str("abc"))), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_string_tag",
  ListItem(ScBytes(b"abc")), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_bytes_tag",
  ListItem(ScString(str("abc"))), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_minor",
  ListItem(ScBytes(b"abc")), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_unknown_relative",
  .List, Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "sha_unknown_absolute",
  .List, Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_hash",
  ListItem(U32(0)), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_hash",
  ListItem(Void), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_hash",
  ListItem(ScString(str("abc"))), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_string_tag",
  ListItem(ScBytes(b"abc")), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_bytes_tag",
  ListItem(ScString(str("abc"))), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_minor",
  ListItem(ScBytes(b"abc")), Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_unknown_relative",
  .List, Error(ErrValue, InvalidInput))

callTx(Account(b"account"), Contract(b"crypto-invalid"), "keccak_unknown_absolute",
  .List, Error(ErrValue, InvalidInput))

setExitCode(0)
