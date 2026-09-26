setExitCode(1)

;; Published empty/abc vectors plus padding, full-rate, and multiblock inputs.
;; Keccak-256 expectations cross-checked with RustCrypto sha3 0.10.8;
;; SHA-256 expectations cross-checked with Python hashlib (FIPS 180-4).
uploadWasm(b"crypto-sha256",
  (module
    (import "c" "_" (func $hash (param i64) (result i64)))
    (func (export "hash") (param i64) (result i64)
      local.get 0
      call $hash)))

setAccount(Account(b"account"), 1000000)
deployContract(Account(b"account"), Contract(b"crypto"), b"crypto-sha256")

;; empty: 0 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"")),
  ScBytes(b"\xe3\xb0\xc4B\x98\xfc\x1c\x14\x9a\xfb\xf4\xc8\x99o\xb9$'\xaeA\xe4d\x9b\x93L\xa4\x95\x99\x1bxR\xb8U"))

;; abc: 3 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"abc")),
  ScBytes(b"\xbax\x16\xbf\x8f\x01\xcf\xeaAA@\xde]\xae\x22#\xb0\x03a\xa3\x96\x17z\x9c\xb4\x10\xffa\xf2\x00\x15\xad"))

;; fips-56: 56 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")),
  ScBytes(b"$\x8dja\xd2\x068\xb8\xe5\xc0&\x93\x0c>`9\xa3<\xe4Yd\xff!g\xf6\xec\xed\xd4\x19\xdb\x06\xc1"))

;; fips-112: 112 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu")),
  ScBytes(b"\xcf[\x16\xa7x\xaf\x83\x80\x03l\xe5\x9e{\x04\x927\x0b$\x9b\x11\xe8\xf0zQ\xaf\xacE\x03z\xfe\xe9\xd1"))

;; a55: 55 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"\x9fC\x90\xf8\xd3\x0c-\xd9.\xc9\xf0\x95\xb6^+\x9a\xe9\xb0\xa9%\xa5%\x8e$\x1c\x9f\x1e\x91\x0fsC\x18"))

;; a56: 56 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"\xb3T9\xa4\xaco\x09H\xb6\xd6\xf9\xe3\xc6\xaf\x0f_Y\x0c\xe2\x0f\x1b\xdep\x90\xefyphn\xc6s\x8a"))

;; a63: 63 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"}>t\xa0]}\xb1[\xceJ\xd9\xec\x06X\xea\x98\xe3\xf0n\xee\xcf\x16\xb4\xc6\xff\xf2\xdaE}\xdc/4"))

;; a64: 64 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"\xff\xe0T\xfez\xe0\xcbm\xc6\x5c:\xf9\xb6\x1dR\x09\xf49\x85\x1d\xb4=\x0b\xa5\x99s7\xdf\x15Fh\xeb"))

;; a65: 65 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"cSa\xc4\x8b\xb9\xea\xb1A\x98\xe7n\xa8\xab\x7f\x1aAh]j\xd6*\xa9\x14m0\x1dO\x17\xeb\x0a\xe0"))

;; a128: 128 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"h6\xcf\x13\xba\xc4\x00\xe9\x10Pq\xcdj\xf4p\x84\xdf\xac\xadN^0,\x94\xbf\xed$\xe0\x13\xaf\xb7>"))

;; a1000: 1000 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
  ScBytes(b"A\xed\xec\xe4-c\xe8\xd9\xbfQZ\x9b\xa6\x93.\x1c \xcb\xc9\xf5\xa5\xd14dZ\xdb]\xb1\xb9s~\xa3"))

;; binary256: 256 bytes
callTx(Account(b"account"), Contract(b"crypto"), "hash",
  ListItem(ScBytes(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !\x22#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\x5c]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff")),
  ScBytes(b"@\xaf\xf2\xe9\xd2\xd8\x92.G\xaf\xd4d\x8eigIqXx_\xbd\x1d\xa8p\xe7\x11\x02f\xbf\x94H\x80"))

setExitCode(0)
