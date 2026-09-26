
```k
requires "address.md"
requires "buffer.md"
requires "call.md"
requires "context.md"
requires "crypto.md"
requires "integer.md"
requires "ledger.md"
requires "map.md"
requires "sparse-map.md"
requires "symbol.md"
requires "vector.md"
requires "xdr.md"

module HOSTFUNS
    imports HOST-ADDRESS
    imports HOST-BUFFER
    imports HOST-CALL
    imports HOST-CONTEXT
    imports HOST-CRYPTO
    imports HOST-INTEGER
    imports HOST-LEDGER
    imports HOST-MAP
    imports HOST-SPARSE-MAP
    imports HOST-SYMBOL
    imports HOST-VECTOR
    imports HOST-XDR

    rule [hostfun-sdk28-invalid-signature]:
        <instrs> hostCall(MOD, FUNC, TYPE) => #throw(ErrWasmVm, InvalidAction) ... </instrs>
      requires notBool sdk28HostSignature(MOD, FUNC, TYPE)
endmodule
```
