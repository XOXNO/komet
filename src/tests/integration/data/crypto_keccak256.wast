setExitCode(1)

;; Published empty/abc vectors plus padding, full-rate, and multiblock inputs.
;; Keccak-256 expectations cross-checked with RustCrypto sha3 0.10.8;
;; SHA-256 expectations cross-checked with Python hashlib (FIPS 180-4).
uploadWasm(b"crypto-keccak256",
  (module
    (import "c" "1" (func $hash (param i64) (result i64)))
    (func (export "hash") (param i64) (result i64)
      local.get 0
      call $hash)))

setAccount(Account(b"account"), 1000000)
deployContract(Account(b"account"), Contract(b"crypto"), b"crypto-keccak256")

;; empty: 0 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"")),
  ScBytes(b"\xc5\xd2F\x01\x86\xf7#<\x92~}\xb2\xdc\xc7\x03\xc0\xe5\x00\xb6S\xca\x82';{\xfa\xd8\x04]\x85\xa4p"))

;; abc: 3 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"abc")),
  ScBytes(b"N\x03ez\xeaE\xa9O\xc7\xd4{\xa8&\xc8\xd6g\xc0\xd1\xe6\xe3:d\xa06\xecD\xf5\x8f\xa1-lE"))

;; quick: 43 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"The quick brown fox jumps over the lazy dog")),
  ScBytes(b"Mt\x1bo\x1e\xb2\x9c\xb2\xa9\xb9\x91\x1c\x82\xf5o\xa8\xd7;\x04\x95\x9d=\x9d\x22(\x95\xdfl\x0b(\xaa\x15"))

;; a135: 135 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"46}\xc2H\xbb\xd82\xf4\xe3\xe6\x9d\xfa\xac/\x92c\x8b\xd0\xbb\xd1\x8f)\x12\xbaN\xf4T\x91\x9c\xf4F"))

;; a136: 136 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"\xa6\xc4\xd4\x03'\x9f\xe3\xe0\xaf\x03r\x9c\xaa\xda\x83t\xb5\xcaT\xd8\x06S)\xa3\xeb\xca\xebK`\xaa8n"))

;; a137: 137 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"\xd8i\xf69\xc7\x04kI)\xfc\x92\xa4\xd9\x88\xa8\xb2,U\xfb\xad\xb8\x02\xc0\xc6n\xbc\xd4\x84\xf1\x91_9"))

;; binary256: 256 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !\x22#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\x5c]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff")),
  ScBytes(b"\xdc\x92Di\xb34\xae\xd2\xa1\x9f\xacrR\xe9\x96\x1a\xeaA\xf8\xd9\x19\x966`)\xdb\xe0\x88B)\xbf6"))

;; a272: 272 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"\xcf\x7f\xcdOp^\xe7I\x93\x0d\x19\xca\x84V\x1a\x9b\xf6%\x16\xbd\x90\xa4qT_\xa2\xf4\x9f\xdc~c\xc8"))

;; a1000: 1000 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"\xb6\xa4\xac\x1fQ\x88Mq\xf3\x0f\xa3\x97\xa5\xe1U\xde0\x99\xe1\x1f\xc0\xed\xef]\x08\xb6F\xe6!\xe1\x9d\xe9"))

setExitCode(0)
