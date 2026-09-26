;; Expected addresses independently computed with Python hashlib + XDR discriminants.
;; Network defaults to 32 zero bytes; constructor failures must leave no instance.
setExitCode(1)



uploadWasm(b"ffffffffffffffffffffffffffffffff",
(module
  (import "l" "e" (func $create (param i64 i64 i64 i64) (result i64)))
  (import "l" "i" (func $reference (param i64 i64 i64 i64 i64) (result i64)))
  (import "l" "h" (func $tag (param i64) (result i64)))
  (import "l" "_" (func $put (param i64 i64 i64) (result i64)))
  (import "l" "2" (func $del (param i64 i64) (result i64)))
  (import "a" "6" (func $executable (param i64) (result i64)))
  (import "d" "0" (func $try_call (param i64 i64 i64) (result i64)))
  (func (export "create") (param i64 i64 i64 i64) (result i64)
    local.get 0 local.get 1 local.get 2 local.get 3 call $create)
  (func (export "reference") (param i64 i64 i64 i64 i64) (result i64)
    local.get 0 local.get 1 local.get 2 call $tag local.get 3 local.get 4 call $reference)
  (func (export "tag") (param i64) (result i64) local.get 0 call $tag)
  (func (export "badtag") (param i64) (result i64) local.get 0 i64.const 256 i64.or call $tag)
  (func (export "badaddr") (param i64) (result i64) local.get 0 i64.const 5 i64.xor call $executable)
  (func (export "missingaddr") (result i64) i64.const 77 call $executable)
  (func (export "invalidreturn") (result i64) i64.const 258)
  (func (export "invalidreturn_object") (result i64) i64.const 72)
  (func (export "invalidreturn_minor") (result i64) i64.const 328)
  (func (export "invalidreturn_tag") (result i64) i64.const 15)
  (func (export "setref") (param i64 i64) (result i64)
    local.get 0 call $tag local.get 1 i64.const 1 call $put)
  (func (export "badref") (param i64 i64) (result i64)
    local.get 0 call $tag local.get 1 i64.const 0 call $put)
  (func (export "delref") (param i64) (result i64)
    local.get 0 call $tag i64.const 1 call $del)
  (func (export "executable") (param i64) (result i64) local.get 0 call $executable)
  (func (export "catch") (param i64 i64 i64) (result i64)
    local.get 0 local.get 1 local.get 2 call $try_call
    i64.const 73014444035 i64.ne if unreachable end i64.const 2)
  (func (export "try") (param i64 i64 i64) (result i64)
    local.get 0 local.get 1 local.get 2 call $try_call)
))

uploadWasm(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
(module
  (import "l" "_" (func $put (param i64 i64 i64) (result i64)))
  (import "l" "1" (func $get (param i64 i64) (result i64)))
  (import "l" "6" (func $update (param i64) (result i64)))
  (func (export "__constructor") (param i64) (result i64)
    i64.const 4 local.get 0 i64.const 1 call $put)
  (func (export "get") (result i64) i64.const 4 i64.const 1 call $get)
  (func (export "update") (param i64) (result i64) local.get 0 call $update)
))

uploadWasm(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
(module (func (export "get") (result i64) i64.const 425201762308)))

uploadWasm(b"cccccccccccccccccccccccccccccccc",
(module
  (import "l" "_" (func $put (param i64 i64 i64) (result i64)))
  (func (export "__constructor") (result i64)
    i64.const 4 i64.const 180388626436 i64.const 1 call $put drop unreachable)
))

uploadWasm(b"dddddddddddddddddddddddddddddddd",
(module (func (export "__constructor") (result i64) i64.const 4)))

setAccount(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), 1000)

deployContract(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), b"ffffffffffffffffffffffffffffffff")



callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "tag", ListItem(ScString(str("release"))), ScExecutableTag(str("release")))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "tag", ListItem(U32(1)), Error(ErrValue, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "badtag", ListItem(ScString(str("release"))), Error(ErrValue, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "badaddr", ListItem(ScBytes(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF")), Error(ErrValue, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "missingaddr", .List, Error(ErrValue, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(MuxedAccount(0, b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))), Error(ErrValue, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))), ScVec(ListItem(Symbol(str("Account")))))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Account(b"ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"))), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"))), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))), ScVec(ListItem(Symbol(str("Wasm"))) ListItem(ScBytes(b"ffffffffffffffffffffffffffffffff"))))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")) ListItem(ScBytes(b"\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e")) ListItem(ScVec(.List)), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")) ListItem(ScBytes(b"\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f")) ListItem(ScVec(ListItem(U32(1)) ListItem(U32(2)))), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")) ListItem(ScBytes(b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01")) ListItem(ScVec(ListItem(U32(17)))), ScAddress(Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7")))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7"), "get", .List, U32(17))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7"))), ScVec(ListItem(Symbol(str("Wasm"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")) ListItem(ScBytes(b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01")) ListItem(ScVec(ListItem(U32(18)))), Error(ErrStorage, ExistingValue))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")) ListItem(ScBytes(b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01")) ListItem(ScVec(.List)), Error(ErrStorage, ExistingValue))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")) ListItem(ScBytes(b"\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02")) ListItem(ScVec(.List)), Error(ErrStorage, MissingValue))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")) ListItem(ScBytes(b"\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03")) ListItem(ScVec(.List)), ScAddress(Contract(b"\xc8\x96\x14\x11?\x0ek@\x9f\xdeho\x82\x00\xf3\x0b\xa9H\x9aub\xb6\x87\x8e58\xe9|9\x87/3")))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")) ListItem(ScBytes(b"\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04")) ListItem(ScVec(ListItem(U32(1)))), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"\xc9\xe4\xfe\x89a\xd0\xd5X\xb8\xf5\x017H\x80F\xc3<_1z\x5c\xbe6p\x9a\xb6\xa8\x81\xca\xea\x1a\xc9"))), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"cccccccccccccccccccccccccccccccc")) ListItem(ScBytes(b"\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05")) ListItem(ScVec(.List)), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"&\xa3o\xbf\xce}\xc0\xb4\x10<\xd6\xb4J\xdd\x9aQ\x81 \xf6\xdf N\xf6b@\xa6\xf7Y\x99\xcc\x92\x09"))), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"dddddddddddddddddddddddddddddddd")) ListItem(ScBytes(b"\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06")) ListItem(ScVec(.List)), Error(ErrValue, UnexpectedType))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"\xc1+\x9bb\x16{\xa1\xc3\x8b!\x9cx^v\xab\xe3\xe8\x0b\xb9d\xfb\x8co|d\xb6;b\x09\xa1A\x8b"))), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"short")) ListItem(ScBytes(b"\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09")) ListItem(ScVec(.List)), Error(ErrObject, UnexpectedSize))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")) ListItem(ScBytes(b"short")) ListItem(ScVec(.List)), Error(ErrObject, UnexpectedSize))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "setref", ListItem(ScString(str("release"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "reference", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScAddress(Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))) ListItem(ScString(str("release"))) ListItem(ScBytes(b"\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07")) ListItem(ScVec(ListItem(U32(23)))), ScAddress(Contract(b"[\x8e#\xe2\xf7\x99\xd3\xd5_\xa7\xe7g\xb6y\x98\x7f R]0\x06\xc3\x04_P\xca\xd0\xcd\xa6\xaeF\x1e")))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"[\x8e#\xe2\xf7\x99\xd3\xd5_\xa7\xe7g\xb6y\x98\x7f R]0\x06\xc3\x04_P\xca\xd0\xcd\xa6\xaeF\x1e"), "get", .List, U32(23))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"[\x8e#\xe2\xf7\x99\xd3\xd5_\xa7\xe7g\xb6y\x98\x7f R]0\x06\xc3\x04_P\xca\xd0\xcd\xa6\xaeF\x1e"))), ScVec(ListItem(Symbol(str("Wasm"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "setref", ListItem(ScString(str("release"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"[\x8e#\xe2\xf7\x99\xd3\xd5_\xa7\xe7g\xb6y\x98\x7f R]0\x06\xc3\x04_P\xca\xd0\xcd\xa6\xaeF\x1e"), "get", .List, U32(99))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"[\x8e#\xe2\xf7\x99\xd3\xd5_\xa7\xe7g\xb6y\x98\x7f R]0\x06\xc3\x04_P\xca\xd0\xcd\xa6\xaeF\x1e"))), ScVec(ListItem(Symbol(str("Wasm"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "delref", ListItem(ScString(str("release"))), Error(ErrStorage, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "badref", ListItem(ScString(str("release"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")), Error(ErrStorage, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "setref", ListItem(ScString(str("release"))) ListItem(U32(1)), Error(ErrStorage, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "setref", ListItem(ScString(str("release"))) ListItem(ScBytes(b"short")), Error(ErrObject, UnexpectedSize))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "setref", ListItem(ScString(str("release"))) ListItem(ScBytes(b"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")), Error(ErrStorage, MissingValue))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"[\x8e#\xe2\xf7\x99\xd3\xd5_\xa7\xe7g\xb6y\x98\x7f R]0\x06\xc3\x04_P\xca\xd0\xcd\xa6\xaeF\x1e"), "get", .List, U32(99))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "reference", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScAddress(Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))) ListItem(ScString(str("missing"))) ListItem(ScBytes(b"\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08")) ListItem(ScVec(.List)), Error(ErrStorage, MissingValue))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "try", ListItem(ScAddress(Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7"))) ListItem(Symbol(str("__constructor"))) ListItem(ScVec(ListItem(U32(90)))), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7"), "get", .List, U32(17))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "setref", ListItem(ScString(str("pinned"))) ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "reference", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScAddress(Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))) ListItem(ScString(str("pinned"))) ListItem(ScBytes(b"\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10")) ListItem(ScVec(ListItem(U32(30)))), ScAddress(Contract(b"9\xca\xd46I\xc5\xcb\xb2\xe6\x0d\xba\xe8\xd8\xf39fVe\x8dI\x93\xb1\xeeO\xbd\xbdU\x85^\xba\x01i")))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"9\xca\xd46I\xc5\xcb\xb2\xe6\x0d\xba\xe8\xd8\xf39fVe\x8dI\x93\xb1\xeeO\xbd\xbdU\x85^\xba\x01i"), "update", ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "setref", ListItem(ScString(str("pinned"))) ListItem(ScBytes(b"cccccccccccccccccccccccccccccccc")), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"9\xca\xd46I\xc5\xcb\xb2\xe6\x0d\xba\xe8\xd8\xf39fVe\x8dI\x93\xb1\xeeO\xbd\xbdU\x85^\xba\x01i"), "get", .List, U32(99))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"9\xca\xd46I\xc5\xcb\xb2\xe6\x0d\xba\xe8\xd8\xf39fVe\x8dI\x93\xb1\xeeO\xbd\xbdU\x85^\xba\x01i"))), ScVec(ListItem(Symbol(str("Wasm"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "reference", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScString(str("release"))) ListItem(ScBytes(b"\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11")) ListItem(ScVec(.List)), Error(ErrStorage, MissingValue))

uploadWasm(b"qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq", (module (func (export "__constructor") (result i64) i64.const 72)))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq")) ListItem(ScBytes(b"\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12\x12")) ListItem(ScVec(.List)), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"\xe27\xd4~\xcf\xba\x07\x88\xf4?\x8a\xd5S\x10\x14-p\xd273\xce\xa2\x90\x9frP\x84M\xad\xae\xa5:"))), Void)

uploadWasm(b"rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr", (module (func (export "__constructor") (result i64) i64.const 15)))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr")) ListItem(ScBytes(b"\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13\x13")) ListItem(ScVec(.List)), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"l\xd2P\x0b\x0e0\x1f\xd4\xf4)\x1c\x5c\xb7(\x9f\xc6\x0e\xe9L\x1aD\xb7d\xb5G\xc0H!@\x17\x95l"))), Void)

uploadWasm(b"ssssssssssssssssssssssssssssssss", (module (func (export "__constructor") (result i64) i64.const 258)))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"ssssssssssssssssssssssssssssssss")) ListItem(ScBytes(b"\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14")) ListItem(ScVec(.List)), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"\xc8#y(\x0a\x0b\xbd\xa0Yf\xb8\x815\x01\x8cM\xbe\xa3{\x84\x03lG\xf4y\xab\xb2\xfa\xf3\xad\xba6"))), Void)

uploadWasm(b"uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu", (module (func (export "__constructor") (result i64) i64.const 21474838275)))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu")) ListItem(ScBytes(b"\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17")) ListItem(ScVec(.List)), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b">\xfbba\xc94\x84\xf8\x80n\xb7\x0b\xbaI\xbd\x5c.\xf4\x85\x0aM\xc4<,#?\xf8F\xebq\x06\x9f"))), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "invalidreturn", .List, Error(ErrValue, UnexpectedType))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "invalidreturn_object", .List, Error(ErrValue, InvalidInput))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "invalidreturn_minor", .List, Error(ErrValue, UnexpectedType))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "invalidreturn_tag", .List, Error(ErrValue, UnexpectedType))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7"), "__constructor", ListItem(U32(91)), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7"), "get", .List, U32(17))

uploadWasm(b"tttttttttttttttttttttttttttttttt",
(module
  (import "l" "_" (func $put (param i64 i64 i64) (result i64)))
  (import "l" "1" (func $get (param i64 i64) (result i64)))
  (func (export "fail") (result i64)
    i64.const 4 i64.const 180388626436 i64.const 1 call $put drop i64.const 73014444035)
  (func (export "get") (result i64) i64.const 4 i64.const 1 call $get)
))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"tttttttttttttttttttttttttttttttt")) ListItem(ScBytes(b"\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16\x16")) ListItem(ScVec(.List)), ScAddress(Contract(b"\xb1h\xd3\xf7\xe9%9\x90\x86~\x93U\x9d\xa7 \xff\xc5\xc4\xfc\xaa\x05\x93\xa9\x0f\x15\x8f.\x86\x16\xc1\xc6\xc2")))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "catch", ListItem(ScAddress(Contract(b"\xb1h\xd3\xf7\xe9%9\x90\x86~\x93U\x9d\xa7 \xff\xc5\xc4\xfc\xaa\x05\x93\xa9\x0f\x15\x8f.\x86\x16\xc1\xc6\xc2"))) ListItem(Symbol(str("fail"))) ListItem(ScVec(.List)), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"\xb1h\xd3\xf7\xe9%9\x90\x86~\x93U\x9d\xa7 \xff\xc5\xc4\xfc\xaa\x05\x93\xa9\x0f\x15\x8f.\x86\x16\xc1\xc6\xc2"), "get", .List, Error(ErrStorage, MissingValue))

uploadWasmWithProtocol(b"pppppppppppppppppppppppppppppppp", (module (func (export "__constructor") (result i64) i64.const 4)), 21)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"pppppppppppppppppppppppppppppppp")) ListItem(ScBytes(b"\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b")) ListItem(ScVec(.List)), ScAddress(Contract(b"\xc0Z\xa3n\x00;#a\x83\x0d\x15\x83\xd7o\xbe\xe1,\x0a9)\xd5\xb1\xdd\x7f5\xc0S=\xef\x115\x01")))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"pppppppppppppppppppppppppppppppp")) ListItem(ScBytes(b"\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c")) ListItem(ScVec(ListItem(U32(1)))), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "executable", ListItem(ScAddress(Contract(b"\xcf\xe8\x04\xdd\x8b%6\x83\xa4#\x88\xfa9\x0b\x90M\xf7;x\xf0h\x15\x1c\xc3i]\x9ay\xa9>\xa1\xf2"))), Void)

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "try", ListItem(ScAddress(Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))) ListItem(Symbol(str("tag"))) ListItem(ScVec(ListItem(ScString(str("release"))))), Error(ErrContext, InvalidAction))

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")) ListItem(ScBytes(b"\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d")) ListItem(ScVec(.List)), ScAddress(Contract(b"\xc2uT\x03#\xf5\xe1\xa2(\x93\xf9\x81(\x86^\x92O)a\xf7C\xecpi)e\x92\xa9\x97\xc1\xd5D")))

setLedgerNetworkId(b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01")

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), "create", ListItem(ScAddress(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))) ListItem(ScBytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")) ListItem(ScBytes(b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01")) ListItem(ScVec(.List)), ScAddress(Contract(b"\xf5\x22\xceh\x1f\x1a\xfe\xbd\xaa\x07\xab\xb0\xb8?7@_B&r\x0d \xd6\x1a\xbe\x92\x17\x9dp\x82\x03Q")))

setLedgerNetworkId(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

callTx(Account(b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), Contract(b".\xf9\xf0]\x81~\xf1\x19)\xa2n)\xa0\xbb`\xe1{\x8a\xf5(\x0dD\x86\xc2k\x0f\xd8\x89\xdb\x9f\x88\xf7"), "get", .List, U32(17))



setExitCode(0)
