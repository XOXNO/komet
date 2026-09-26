setExitCode(1)

uploadWasm(b"sdk28-values",
(module
  (import "x" "0" (func $obj_cmp (param i64 i64) (result i64)))
  (func $echo (param i64) (result i64)
    local.get 0
  )
  (func $tag (param i64) (result i64)
    local.get 0
    i64.const 255
    i64.and
    i64.const 32
    i64.shl
    i64.const 4
    i64.or
  )
  (func $compare (param i64 i64) (result i64)
    (call $obj_cmp (local.get 0) (local.get 1))
    i64.const 8
    i64.shl
    i64.const 7
    i64.or
  )
  (export "echo" (func $echo))
  (export "tag" (func $tag))
  (export "compare" (func $compare))
))

setAccount(Account(b"test-account"), 9876543210)
deployContract(Account(b"test-account"), Contract(b"test-sc"), b"sdk28-values")

;; Zero, small-value limit, first object value, and u64 limit.
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScTimepoint(0)), ScTimepoint(0))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScTimepoint(72057594037927935)), ScTimepoint(72057594037927935))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScTimepoint(72057594037927936)), ScTimepoint(72057594037927936))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScTimepoint(18446744073709551615)), ScTimepoint(18446744073709551615))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScDuration(0)), ScDuration(0))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScDuration(72057594037927935)), ScDuration(72057594037927935))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScDuration(72057594037927936)), ScDuration(72057594037927936))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScDuration(18446744073709551615)), ScDuration(18446744073709551615))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScExecutableTag(str("release"))), ScExecutableTag(str("release")))
callTx(Account(b"test-account"), Contract(b"test-sc"), "echo", ListItem(ScAddress(MuxedAccount(18446744073709551615, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))), ScAddress(MuxedAccount(18446744073709551615, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")))

;; Small and object tags survive relative-handle conversion.
callTx(Account(b"test-account"), Contract(b"test-sc"), "tag", ListItem(ScTimepoint(72057594037927935)), U32(8))
callTx(Account(b"test-account"), Contract(b"test-sc"), "tag", ListItem(ScTimepoint(72057594037927936)), U32(66))
callTx(Account(b"test-account"), Contract(b"test-sc"), "tag", ListItem(ScDuration(72057594037927935)), U32(9))
callTx(Account(b"test-account"), Contract(b"test-sc"), "tag", ListItem(ScDuration(72057594037927936)), U32(67))
callTx(Account(b"test-account"), Contract(b"test-sc"), "tag", ListItem(ScAddress(MuxedAccount(0, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))), U32(78))
callTx(Account(b"test-account"), Contract(b"test-sc"), "tag", ListItem(ScExecutableTag(str("release"))), U32(79))

;; XDR variant order, integer order, and muxed id-before-key order.
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScTimepoint(18446744073709551615)) ListItem(ScDuration(0)), I64(-1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScTimepoint(72057594037927936)) ListItem(ScTimepoint(72057594037927935)), I64(1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScDuration(72057594037927935)) ListItem(ScDuration(72057594037927936)), I64(-1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScAddress(Contract(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))) ListItem(ScExecutableTag(str(""))), I64(-1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScExecutableTag(str("a"))) ListItem(ScExecutableTag(str("b"))), I64(-1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScAddress(Contract(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))) ListItem(ScAddress(MuxedAccount(0, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))), I64(-1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScAddress(MuxedAccount(0, b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))) ListItem(ScAddress(MuxedAccount(1, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))), I64(-1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScAddress(MuxedAccount(1, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))) ListItem(ScAddress(MuxedAccount(1, b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))), I64(-1))
callTx(Account(b"test-account"), Contract(b"test-sc"), "compare", ListItem(ScAddress(MuxedAccount(1, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))) ListItem(ScAddress(MuxedAccount(1, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))), I64(0))

setExitCode(0)
