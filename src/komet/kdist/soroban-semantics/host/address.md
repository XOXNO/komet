# ADDRESS

```k
requires "../configuration.md"
requires "../switch.md"
requires "../wasm-ops.md"
requires "integer.md"
requires "arguments.md"

module HOST-ADDRESS
    imports CONFIG-OPERATIONS
    imports WASM-OPERATIONS
    imports HOST-INTEGER
    imports HOST-ARGUMENTS
    imports SWITCH-SYNTAX

```

## require_auth

```k
    // TODO This is just a placeholder, as the auth system is out of scope for now.
    // This function needs to be properly implemented to handle the authorization.
    rule [hostfun-require-auth]:
        <instrs> hostCall ( "a" , "0" , [ i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => toSmall(Void)
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > _      // Address
        </locals>
```

## authorize_as_curr_contract

```k
    rule [hostfun-authorize-as-curr-contract]:
        <instrs> hostCall ( "a" , "3" , [ i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => toSmall(Void)
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > _
        </locals>

    // get_address_executable

    rule [hostfun-get-address-executable]:
        <instrs> hostCallAux("a", "6") => addressExecutable(ADDR) ... </instrs>
        <hostStack> ScAddress(ADDR) : S => S </hostStack>

    rule [hostfun-get-address-executable-type]:
        <instrs> hostCallAux("a", "6") => #throw(ErrValue, UnexpectedType) ... </instrs>
      [owise]

    syntax InternalInstr ::= addressExecutable(Address) | executableValue(ContractExecutable)

    rule [addressExecutable-account]:
        <instrs> addressExecutable(ADDR:AccountId)
              => allocObject(ScVec(ListItem(Symbol("Account")))) ~> returnHostVal ... </instrs>
        <account> <accountId> ADDR </accountId> ... </account>

    rule [addressExecutable-contract]:
        <instrs> addressExecutable(ADDR:ContractId) => executableValue(EXEC) ... </instrs>
        <contract> <contractId> ADDR </contractId> <contractExecutable> EXEC </contractExecutable> ... </contract>

    rule [addressExecutable-missing]:
        <instrs> addressExecutable(_) => toSmall(Void) ... </instrs>
      [owise]

    rule [addressExecutable-muxed]:
        <instrs> addressExecutable(MuxedAccount(_, _)) => #throw(ErrValue, UnexpectedType) ... </instrs>

    rule [executableValue-wasm]:
        <instrs> executableValue(Wasm(HASH))
              => allocObject(ScVec(ListItem(Symbol("Wasm")) ListItem(ScBytes(HASH)))) ~> returnHostVal ... </instrs>

    rule [executableValue-asset]:
        <instrs> executableValue(StellarAsset)
              => allocObject(ScVec(ListItem(Symbol("StellarAsset")))) ~> returnHostVal ... </instrs>

    rule [executableValue-reference]:
        <instrs> executableValue(ExternalRef(OWNER, TAG)) => executableValue(Wasm(HASH)) ... </instrs>
        <contractData> ... #skey(OWNER, #persistent, ScExecutableTag(TAG)) |-> #sval(ScBytes(HASH), _) ... </contractData>
      requires lengthBytes(HASH) ==Int 32

    rule [executableValue-reference-missing]:
        <instrs> executableValue(ExternalRef(_, _)) => #throw(ErrStorage, MissingValue) ... </instrs>
      [owise]

    rule [hostfun-a-6-checked-inputs]:
        <instrs> hostCall("a", "6", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => loadArgs(1) ~> hostCallAux("a", "6") ... </instrs>
        <locals> 0 |-> <i64> V0 </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires hostTypedRef(HostVal(V0), 77, OBJS, RELS)

    rule [hostfun-a-6-invalid-inputs]:
        <instrs> hostCall("a", "6", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
      [priority(60)]

endmodule
```
