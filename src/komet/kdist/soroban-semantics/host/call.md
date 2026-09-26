# Call

```k
requires "../configuration.md"
requires "../switch.md"
requires "../soroban.md"
requires "integer.md"

module HOST-CALL
    imports WASM-OPERATIONS
    imports SOROBAN-SYNTAX
    imports HOST-INTEGER

```

## call

```k
    // Reentry is checked by the shared callContract command.
    rule [hostCallAux-call]:
        <instrs> hostCallAux ( "d" , "_" )
              => #waitCommands
              ~> returnCallResult
                 ...
        </instrs>
        <hostStack> ScAddress(TO) : Symbol(FUNC) : ScVec(ARGS) : S => S </hostStack>
        <callee> FROM </callee>
        <k> (.K => callContract(FROM, TO, FUNC, ARGS)) ... </k>
      requires substrString(FUNC, 0, minInt(2, lengthString(FUNC))) =/=String "__"


    rule [hostCallAux-call-reserved]:
        <instrs> hostCallAux("d", "_") => #throw(ErrContext, InvalidAction) ... </instrs>
        <hostStack> ScAddress(_) : Symbol(FUNC) : ScVec(_) : S => S </hostStack>
      requires substrString(FUNC, 0, minInt(2, lengthString(FUNC))) ==String "__"

    rule [hostCallAux-try-call-reserved]:
        <instrs> hostCallAux("d", "0") => allocObject(Error(ErrContext, InvalidAction)) ~> returnHostVal ... </instrs>
        <hostStack> ScAddress(_) : Symbol(FUNC) : ScVec(_) : S => S </hostStack>
      requires substrString(FUNC, 0, minInt(2, lengthString(FUNC))) ==String "__"

    syntax InternalInstr ::= "returnCallResult"   [symbol(returnCallResult)]
 // ------------------------------------------------------------------------
    rule [returnCallResult-error]:
        <instrs> returnCallResult ~> _ => .K </instrs>
        <hostStack> Error(_,_) : _ </hostStack>
    
    rule [returnCallResult]:
        <instrs> returnCallResult
              => allocObject(RES)
              ~> returnHostVal
                 ...
        </instrs>
        <hostStack> RES:ScVal : S => S </hostStack>
      [owise]
```

## try_call

```k
    // Reentry is checked by the shared callContract command.
    rule [hostCallAux-try-call]:
        <instrs> hostCallAux ( "d" , "0" )
              => #waitCommands
              ~> returnTryCallResult
                 ...
        </instrs>
        <hostStack> ScAddress(TO) : Symbol(FUNC) : ScVec(ARGS) : S => S </hostStack>
        <callee> FROM </callee>
        <k> (.K => callContract(FROM, TO, FUNC, ARGS)) ... </k>
      requires substrString(FUNC, 0, minInt(2, lengthString(FUNC))) =/=String "__"

    syntax InternalInstr ::= "returnTryCallResult"   [symbol(returnTryCallResult)]
 // ------------------------------------------------------------------------
    rule [returnTryCallResult-recoverable]:
        <instrs> returnTryCallResult
              => allocObject( #if ET ==K ErrContract
                    #then ERR
                    #else Error(ErrContext, InvalidAction)
                    #fi )
              ~> returnHostVal
                 ...
        </instrs>
        <hostStack> (Error(ET,CODE) #as ERR) : S => S </hostStack>
      requires isRecoverable(ET, CODE)

    rule [returnTryCallResult-not-recoverable]:
        <instrs> returnTryCallResult ~> _ => .K </instrs>
        <hostStack> Error(ET,CODE) : _ </hostStack>
      requires notBool isRecoverable(ET, CODE)

    rule [returnTryCallResult-ok]:
        <instrs> returnTryCallResult
              => allocObject(RES)
              ~> returnHostVal
                 ...
        </instrs>
        <hostStack> RES:ScVal : S => S </hostStack>
      [owise]
```
### Recoverable errors

[Rust Source](https://github.com/stellar/rs-soroban-env/blob/9c7f5e36df18c50d9cf24ee4cd5102dabedd708c/soroban-env-host/src/host/error.rs#L159)

```k
    syntax Bool ::= isRecoverable(ErrorType, Int)   [function, total]
 // -----------------------------------------------------------------
    rule isRecoverable(ET, CODE) => notBool (
               ( ET =/=K ErrContract andBool CODE ==Int InternalError )
        orBool ( ET ==K  ErrStorage  andBool CODE ==Int ExceededLimit )
        orBool ( ET ==K  ErrBudget   andBool CODE ==Int ExceededLimit ) )

endmodule
```