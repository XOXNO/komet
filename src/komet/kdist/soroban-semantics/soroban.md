

```k
requires "configuration.md"
requires "switch.md"
requires "host/hostfuns.md"

module SOROBAN-SYNTAX
    imports HOST-OBJECT-SYNTAX

    syntax InternalCmd ::= callContract ( Address, ContractId, String, List ) [symbol(callContractString), function, total]

endmodule


module SOROBAN
    imports SOROBAN-SYNTAX
    imports CONFIG-OPERATIONS
    imports SWITCH
    imports HOSTFUNS
```

## Contract Call

Invoking a contract is split across three commands that hand off to one another:

- `callContract` orchestrates the call: saves the caller's state and arranges for it to be restored (or discarded)
  once the callee is done.
- `callContractAux` resolves the callee's code and instantiates a fresh Wasm module for it.
- `mkCall` performs the actual invocation against that instance.

Once the callee's Wasm finishes executing, `#endWasm` (see `switch.md`) switches control back to `<k>` and restores
the caller.

**WARNING**: `trace-callContract` in `tracing.md` duplicates the transition of `callContract` below to log a call's
start. If you change this rule, you must update that too, or tracing will silently drift out of sync with the real
semantics.

```k

    syntax InternalCmd ::= callContract    ( Address, ContractId, WasmString, List ) [symbol(callContractWasmString)]
                         | callContractAux ( Address, ContractId, WasmString, List ) [symbol(callContractAux)]
 // -------------------------------------------------------------------------------------
    rule callContract(FROM, TO, FUNCNAME:String, ARGS)
      => callContract(FROM, TO, #quoteUnparseWasmString(FUNCNAME), ARGS)

    // Orchestrates a contract call: saves the caller's world/call state so it can be restored afterwards,
    // resets the active call state for the callee, delegates to `callContractAux` to set up and invoke the
    // callee, and queues `#endWasm` to switch back to `<k>` and restore the caller once the callee finishes.
    rule [callContract]:
        <k> callContract(FROM, TO, FUNCNAME:WasmStringToken, ARGS)
         => pushWorldState
         ~> pushCallState
         ~> resetCallstate
         ~> callContractAux(FROM, TO, FUNCNAME, ARGS)
         ~> #endWasm
            ...
        </k>
        <activeContracts> ACTIVE => ListItem(TO) ACTIVE </activeContracts>
      requires notBool (TO in ACTIVE)

    rule [callContract-reentry]:
        <k> callContract(_, TO, _:WasmStringToken, _) => pushStack(Error(ErrContext, InvalidAction)) ... </k>
        <activeContracts> ACTIVE </activeContracts>
      requires TO in ACTIVE

    // Looks up the callee's code and instantiates a fresh Wasm module for it, then delegates to `mkCall`
    // to actually invoke the requested function once that instance exists.
    rule [callContractAux]:
        <k> callContractAux(FROM, TO, FUNCNAME, ARGS)
         => newWasmInstance(TO, CODE)
         ~> mkCall(FROM, TO, FUNCNAME, ARGS)
            ...
        </k>
        <contract>
          <contractId> TO </contractId>
          <contractExecutable> Wasm(HASH) </contractExecutable>
          ...
        </contract>
        <contractCode>
          <codeHash> HASH </codeHash>
          <codeWasm> CODE </codeWasm>
          ...
        </contractCode>
        <instrs> .K </instrs>

    rule [callContractAux-reference]:
        <k> callContractAux(FROM, TO, FUNCNAME, ARGS)
         => newWasmInstance(TO, CODE) ~> mkCall(FROM, TO, FUNCNAME, ARGS) ... </k>
        <contract> <contractId> TO </contractId> <contractExecutable> ExternalRef(OWNER, TAG) </contractExecutable> ... </contract>
        <contractData> ... #skey(OWNER, #persistent, ScExecutableTag(TAG)) |-> #sval(ScBytes(HASH), _) ... </contractData>
        <contractCode> <codeHash> HASH </codeHash> <codeWasm> CODE </codeWasm> ... </contractCode>
        <instrs> .K </instrs>
      requires lengthBytes(HASH) ==Int 32

    rule [callContractAux-missing]:
        <k> callContractAux(_, _, _, _) => pushStack(Error(ErrStorage, MissingValue)) ... </k>
        <instrs> .K </instrs>
      [owise]

    syntax WasmCell
    syntax InternalCmd ::= newWasmInstance   (ContractId, ModuleDecl)     [symbol(newWasmInstance)]
                         | newWasmInstanceAux(ContractId, ModuleDecl)     [symbol(newWasmInstanceAux)]

    rule [newWasmInstance]:
        <k> newWasmInstance(ADDR, CODE) => newWasmInstanceAux(ADDR, CODE) ... </k>
        <instrs> .K </instrs>

    rule [newWasmInstanceAux]:
        <k> newWasmInstanceAux(_, CODE) => #waitWasm ~> setContractModIdx ... </k>
        ( _:WasmCell => <wasm>
          <instrs> initContractModule(CODE) </instrs>
          ...
        </wasm>)
      // TODO: It is fairly hard to check that this rule preserves definedness.
      // However, if that's not the case, then this axiom is invalid. We should
      // figure this out somehow. Preferably, we should make initContractModule
      // a total function. Otherwise, we should probably make a
      // `definedInitContractModule` function that we should use in the requires
      // clause.

    syntax InternalCmd ::= "setContractModIdx"
 // ------------------------------------------------------
    rule [setContractModIdx]:
        <k> setContractModIdx => .K ... </k>
        <contractModIdx> _ => NEXTIDX -Int 1 </contractModIdx>
        <nextModuleIdx> NEXTIDX </nextModuleIdx>
        <instrs> .K </instrs>

    syntax K ::= initContractModule(ModuleDecl)   [function]
 // ------------------------------------------------------------------------
    rule initContractModule((module _:OptionalId _:Defns):ModuleDecl #as M)
      => sequenceStmts(text2abstract(M .Stmts))

    rule initContractModule(M:ModuleDecl) => M              [owise]


    syntax InternalCmd ::= mkCall( Address, ContractId, WasmString, List )  [symbol(mkCall)]
 // ------------------------------------------------------------------------
    // Performs the actual invocation once the callee's Wasm instance exists: populates the (already-reset)
    // call state with caller/callee/function/args, resolves FUNCNAME to a function index in the instance's
    // exports, and sets `<instrs>` to push the (HostVal) args and invoke that function.
    rule [mkCall]:
        <k> mkCall(FROM, TO, FUNCNAME:WasmStringToken, ARGS) => .K ... </k>
        <callState>
          <caller> _ => FROM </caller>
          <callee> _ => TO   </callee>
          <function> _ => FUNCNAME </function>
          <args> _ => ARGS </args>
          <wasm>
            <instrs> .K => pushArgs(ARGS) ~> (invoke (FUNCADDRS {{ FUNCIDX }} orDefault -1 )) </instrs>
            <moduleInst>
              <modIdx> MODIDX </modIdx>
              <exports> ... FUNCNAME |-> FUNCIDX:Int ... </exports>
              <funcAddrs> FUNCADDRS </funcAddrs>
              ...
            </moduleInst>
            <funcDef>
              <fAddr> FADDR </fAddr>
              <fType> [ DOMAIN ] -> [ i64 .ValTypes ] </fType>
              ...
            </funcDef>
            ...
          </wasm>
          <contractModIdx> MODIDX:Int </contractModIdx>
          ...
        </callState>
        requires isListIndex(FUNCIDX, FUNCADDRS)
         andBool FADDR ==Int (FUNCADDRS {{ FUNCIDX }} orDefault -1)
         andBool size(ARGS) ==Int lengthValTypes(DOMAIN)
         andBool size(ARGS) <=Int 32 andBool i64Parameters(DOMAIN)
      [priority(60)]

    syntax Bool ::= i64Parameters(ValTypes) [function, total]
    rule i64Parameters(.ValTypes) => true
    rule i64Parameters(i64 REST) => i64Parameters(REST)
    rule i64Parameters(_) => false [owise]

    rule [mkCall-too-many-arguments]:
        <k> mkCall(_, _, _:WasmStringToken, ARGS) => pushStack(Error(ErrWasmVm, InvalidInput)) ... </k>
      requires size(ARGS) >Int 32
      [priority(40)]

    rule [mkCall-wrong-arity]:
        <k> mkCall(_, _, FUNCNAME:WasmStringToken, ARGS) => pushStack(Error(ErrWasmVm, UnexpectedSize)) ... </k>
        <contractModIdx> MODIDX:Int </contractModIdx>
        <moduleInst> <modIdx> MODIDX </modIdx> <exports> ... FUNCNAME |-> IDX:Int ... </exports> <funcAddrs> ADDRS </funcAddrs> ... </moduleInst>
        <funcDef> <fAddr> FADDR </fAddr> <fType> [ DOMAIN ] -> [ RANGE ] </fType> ... </funcDef>
      requires isListIndex(IDX, ADDRS) andBool FADDR ==Int (ADDRS {{ IDX }} orDefault -1)
       andBool (size(ARGS) =/=Int lengthValTypes(DOMAIN) orBool lengthValTypes(RANGE) =/=Int 1)

    rule [mkCall-wrong-type]:
        <k> mkCall(_, _, FUNCNAME:WasmStringToken, ARGS) => pushStack(Error(ErrWasmVm, UnexpectedType)) ... </k>
        <contractModIdx> MODIDX:Int </contractModIdx>
        <moduleInst> <modIdx> MODIDX </modIdx> <exports> ... FUNCNAME |-> IDX:Int ... </exports> <funcAddrs> ADDRS </funcAddrs> ... </moduleInst>
        <funcDef> <fAddr> FADDR </fAddr> <fType> [ DOMAIN ] -> [ RANGE ] </fType> ... </funcDef>
      requires isListIndex(IDX, ADDRS) andBool FADDR ==Int (ADDRS {{ IDX }} orDefault -1)
       andBool size(ARGS) ==Int lengthValTypes(DOMAIN) andBool lengthValTypes(RANGE) ==Int 1
       andBool notBool (i64Parameters(DOMAIN) andBool i64Parameters(RANGE))

    // A protocol-22+ absent constructor is a no-op only for zero arguments.
    rule [mkCall-default-constructor]:
        <k> mkCall(_, _, FUNCNAME:WasmStringToken, .List) => .K ... </k>
        <contractModIdx> MODIDX:Int </contractModIdx>
        <moduleInst> <modIdx> MODIDX </modIdx> <exports> EXPORTS </exports> ... </moduleInst>
        <valstack> _ => <i64> 2 : .ValStack </valstack>
      requires wasmString2StringStripped(FUNCNAME) ==String "__constructor"
       andBool notBool (FUNCNAME in_keys(EXPORTS))

    rule [mkCall-missing]:
        <k> mkCall(_, _, FUNCNAME:WasmStringToken, ARGS) => pushStack(Error(ErrWasmVm, MissingValue)) ... </k>
        <contractModIdx> MODIDX:Int </contractModIdx>
        <moduleInst> <modIdx> MODIDX </modIdx> <exports> EXPORTS </exports> ... </moduleInst>
      requires notBool (FUNCNAME in_keys(EXPORTS))
       andBool (wasmString2StringStripped(FUNCNAME) =/=String "__constructor" orBool size(ARGS) >Int 0)

    syntax InternalInstr ::= pushArgs(List)      [symbol(pushArgs)]
                           | pushArg(HostVal)    [symbol(pushArg)]
 // ---------------------------------------------------------------------
    rule [pushArgs-empty]:
        <instrs> pushArgs(.List) => .K ... </instrs>

    rule [pushArgs]:
        <instrs> pushArgs(ListItem(ARG:HostVal) ARGS) => pushArg(ARG) ~> pushArgs(ARGS) ... </instrs>
    
    rule [pushArg-not-obj]:
        <instrs> pushArg(VAL) => VAL ... </instrs>
      requires notBool isObject(VAL)

    rule [pushArg-obj-rel]:
        <instrs> pushArg(VAL) => trap ... </instrs>
      requires isObject(VAL)
       andBool isRelativeObjectHandle(VAL) // there should not be any relative objects in this context

    rule [pushArg-obj-abs]:
        <instrs> pushArg(VAL) 
              => fromHandleAndTag(indexToHandle(size(RELS), true) , getTag(VAL)) 
                 ...
        </instrs>
        <relativeObjects> RELS => RELS ListItem(VAL) </relativeObjects>
      requires isObject(VAL)
       andBool (notBool isRelativeObjectHandle(VAL))

    rule [push-HostVal]:
        <instrs> HostVal(I) => i64.const I ... </instrs>

```


```k
endmodule
```
