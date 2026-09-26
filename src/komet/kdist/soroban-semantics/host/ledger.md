# Ledger Host Functions

```k
requires "integer.md"
requires "arguments.md"
requires "crypto.md"
requires "call.md"
requires "../soroban.md"

module HOST-LEDGER
    imports HOST-INTEGER
    imports HOST-ARGUMENTS
    imports SOROBAN-CRYPTO
    imports HOST-CALL
    imports SOROBAN-SYNTAX

```

## put_contract_data

```k
    rule [hostfun-put-contract-data]:
        <instrs> hostCall ( "l" , "_" , [ i64  i64  i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => loadObjectFull(HostVal(VAL))
              ~> loadObjectFull(HostVal(KEY))
              ~> validatePutContractData(Int2StorageType(STORAGE_TYPE))
              ~> putContractData(Int2StorageType(STORAGE_TYPE))
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > KEY            // HostVal
          1 |-> < i64 > VAL            // HostVal
          2 |-> < i64 > STORAGE_TYPE   // 0: temp, 1: persistent, 2: instance
        </locals>
      requires Int2StorageTypeValid(STORAGE_TYPE)

    syntax InternalInstr ::= putContractData(StorageType)   [symbol(putContractData)]
 // ---------------------------------------------------------------------------------
    rule [putContractData-instance]:
        <instrs> putContractData(#instance) => toSmall(Void) ... </instrs>
        <hostStack> KEY : VAL : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contract>
          <contractId> CONTRACT </contractId>
          <instanceStorage> STORAGE => STORAGE [ KEY <- VAL ] </instanceStorage>
          ...
        </contract>

    rule [putContractData-other-existing]:
        <instrs> putContractData(DUR:Durability) => toSmall(Void) ... </instrs>
        <hostStack> KEY : VAL : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contractData>
          ...
          #skey(CONTRACT, DUR, KEY) |-> #sval(_ => VAL, _LIVE_UNTIL)
          ...
        </contractData>

    rule [putContractData-other-new]:
        <instrs> putContractData(DUR:Durability) => toSmall(Void) ... </instrs>
        <hostStack> KEY : VAL : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contractData>
          STORAGE => STORAGE [ #skey(CONTRACT, DUR, KEY) <- #sval(VAL, minLiveUntil(DUR, SEQ)) ]
        </contractData>
        <ledgerSequenceNumber> SEQ </ledgerSequenceNumber>
      requires notBool( #skey(CONTRACT, DUR, KEY) in_keys(STORAGE) )

```

## has_contract_data

```k
    rule [hostfun-has-contract-data]:
        <instrs> hostCall ( "l" , "0" , [ i64  i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => loadObjectFull(HostVal(KEY))
              ~> hasContractData(Int2StorageType(STORAGE_TYPE))
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > KEY            // HostVal
          1 |-> < i64 > STORAGE_TYPE   // 0: temp, 1: persistent, 2: instance
        </locals>
      requires Int2StorageTypeValid(STORAGE_TYPE)

    syntax InternalInstr ::= hasContractData(StorageType)   [symbol(hasContractData)]
 // ---------------------------------------------------------------------------------
    rule [hasContractData-instance]:
        <instrs> hasContractData(#instance)
              => toSmall(SCBool( KEY in_keys(STORAGE) ))
                 ...
        </instrs>
        <hostStack> KEY : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contract>
          <contractId> CONTRACT </contractId>
          <instanceStorage> STORAGE </instanceStorage>
          ...
        </contract>

    rule [hasContractData-other]:
        <instrs> hasContractData(DUR:Durability)
              => toSmall(SCBool( #skey(CONTRACT, DUR, KEY) in_keys(STORAGE) ))
                 ...
        </instrs>
        <hostStack> KEY : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contractData> STORAGE </contractData>
```

## get_contract_data

```k
    rule [hostfun-get-contract-data]:
        <instrs> hostCall ( "l" , "1" , [ i64  i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => loadObjectFull(HostVal(KEY))
              ~> getContractData(Int2StorageType(STORAGE_TYPE))
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > KEY            // HostVal
          1 |-> < i64 > STORAGE_TYPE   // 0: temp, 1: persistent, 2: instance
        </locals>
      requires Int2StorageTypeValid(STORAGE_TYPE)

    syntax InternalInstr ::= getContractData(StorageType)   [symbol(getContractData)]
 // ---------------------------------------------------------------------------------
    rule [getContractData-instance]:
        <instrs> getContractData(#instance)
              => allocObject(VAL)
              ~> returnHostVal
                 ...
        </instrs>
        <hostStack> KEY : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contract>
          <contractId> CONTRACT </contractId>
          <instanceStorage> ... KEY |-> VAL ... </instanceStorage>
          ...
        </contract>

    rule [getContractData-other]:
        <instrs> getContractData(DUR:Durability)
              => allocObject(VAL)
              ~> returnHostVal
                 ...
        </instrs>
        <hostStack> KEY : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contractData> ... #skey(CONTRACT, DUR, KEY) |-> #sval(VAL, _) ... </contractData>

```

## del_contract_data

```k
    rule [hostfun-del-contract-data]:
        <instrs> hostCall ( "l" , "2" , [ i64  i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => loadObjectFull(HostVal(KEY))
              ~> validateDelContractData
              ~> delContractData(Int2StorageType(STORAGE_TYPE))
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > KEY            // HostVal
          1 |-> < i64 > STORAGE_TYPE   // 0: temp, 1: persistent, 2: instance
        </locals>
      requires Int2StorageTypeValid(STORAGE_TYPE)

    syntax InternalInstr ::= delContractData(StorageType)   [symbol(delContractData)]
 // ---------------------------------------------------------------------------------
    rule [delContractData-instance]:
        <instrs> delContractData(#instance) => toSmall(Void) ... </instrs>
        <hostStack> KEY : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contract>
          <contractId> CONTRACT </contractId>
          <instanceStorage> MAP => MAP [ KEY <- undef ] </instanceStorage>
          ...
        </contract>
      requires KEY in_keys(MAP)

    rule [delContractData-other]:
        <instrs> delContractData(DUR:Durability) => toSmall(Void) ... </instrs>
        <hostStack> KEY : S => S </hostStack>
        <callee> CONTRACT </callee>
        <contractData> MAP => MAP [#skey(CONTRACT, DUR, KEY) <- undef ] </contractData>
      requires #skey(CONTRACT, DUR, KEY) in_keys(MAP)

```
## update_current_contract_wasm

```k
    rule [hostfun-update-current-contract-wasm]:
        <instrs> hostCall ( "l" , "6" , [ i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => loadObject(HostVal(HASH))
              ~> updateContractWasm(CALLEE)
              ~> toSmall(Void)
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > HASH   // Bytes
        </locals>
        <callee> CALLEE </callee>

    syntax InternalInstr ::= updateContractWasm(ContractId)   [symbol(updateContractWasm)]
 // --------------------------------------------------------------------------------------
    rule [updateContractWasm]:
        <instrs> updateContractWasm(CONTRACT) => .K ... </instrs>
        <hostStack> ScBytes(HASH) : S => S </hostStack>
        <contract>
          <contractId> CONTRACT </contractId>
          <contractExecutable> _ => Wasm(HASH) </contractExecutable>
          ...
        </contract>
        <contractCode>
          <codeHash> HASH </codeHash>
          ...
        </contractCode>

```

## extend_contract_data_ttl

```k
    rule [hostfun-extend-contract-data-ttl]:
        <instrs> hostCall ( "l" , "7" , [ i64  i64  i64  i64 .ValTypes ] -> [ i64  .ValTypes ] )
              => loadObject(HostVal(EXTEND_TO))
              ~> loadObject(HostVal(THRESHOLD))
              ~> loadObjectFull(HostVal(KEY))
              ~> extendContractDataTtl(CONTRACT, Int2StorageType(STORAGE_TYPE))
              ~> toSmall(Void)
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > KEY            // HostVal
          1 |-> < i64 > STORAGE_TYPE   // 0: temp, 1: persistent, 2: instance
          2 |-> < i64 > THRESHOLD   // U32
          3 |-> < i64 > EXTEND_TO   // U32
        </locals>
        <callee> CONTRACT </callee>
      requires Int2StorageTypeValid(STORAGE_TYPE)

    syntax InternalInstr ::= extendContractDataTtl(Address, StorageType)   [symbol(extendContractDataTtl)]
 // --------------------------------------------------------------------------------------------
    rule [extendContractDataTtl]:
        <instrs> extendContractDataTtl(CONTRACT, DUR:Durability) => .K ... </instrs>
        <hostStack> KEY:ScVal : U32(THRESHOLD) : U32(EXTEND_TO) : S => S </hostStack>
        <contractData>
          ...
          #skey(CONTRACT, DUR, KEY)
            |-> #sval(_VAL, LIVE_UNTIL => extendedLiveUntil(SEQ, LIVE_UNTIL, THRESHOLD, EXTEND_TO))
          ... 
        </contractData>
        <ledgerSequenceNumber> SEQ </ledgerSequenceNumber>
      requires THRESHOLD <=Int EXTEND_TO   // input is valid
       andBool SEQ <=Int LIVE_UNTIL        // entry is alive
       andBool ( DUR =/=K #temporary 
          orBool extendedLiveUntil(SEQ, LIVE_UNTIL, THRESHOLD, EXTEND_TO) <=Int maxLiveUntil(SEQ)
       ) // #temporary TTLs has to be exact

    rule [extendContractDataTtl-err]:
        <instrs> extendContractDataTtl(_CONTRACT, _TYP) => #throw(ErrStorage, InvalidAction) ... </instrs>
        <hostStack> _KEY:ScVal : U32(_THRESHOLD) : U32(_EXTEND_TO) : S => S </hostStack>
      [owise]

```

## extend_current_contract_instance_and_code_ttl

```k
    rule [hostfun-extend-current-contract-instance-and-code-ttl]:
        <instrs> hostCall ( "l" , "8" , [ i64  i64  .ValTypes ] -> [ i64  .ValTypes ] )
              => loadObject(HostVal(EXTEND_TO))
              ~> loadObject(HostVal(THRESHOLD))
              ~> extendContractTtl(CONTRACT)
              ~> loadObject(HostVal(EXTEND_TO))
              ~> loadObject(HostVal(THRESHOLD))
              ~> extendContractCodeTtl(CONTRACT)
              ~> toSmall(Void)
                 ...
        </instrs>
        <locals>
          0 |-> < i64 > THRESHOLD   // U32
          1 |-> < i64 > EXTEND_TO   // U32
        </locals>
        <callee> CONTRACT </callee>

  // If the TTL for the contract is less than or equal to `THRESHOLD`,
  // update <contractLiveUntil>
    syntax InternalInstr ::= extendContractTtl(ContractId)   [symbol(extendContractTtl)]
 // -------------------------------------------------------------------------------
    rule [extendContractTtl]:
        <instrs> extendContractTtl(CONTRACT) => .K ... </instrs>
        <hostStack> U32(THRESHOLD) : U32(EXTEND_TO) : S => S </hostStack>
        <contract>
          <contractId> CONTRACT </contractId>
          <contractLiveUntil> LIVE_UNTIL
                           => extendedLiveUntil(SEQ, LIVE_UNTIL, THRESHOLD, EXTEND_TO)
          </contractLiveUntil>
          ...
        </contract>
        <ledgerSequenceNumber> SEQ </ledgerSequenceNumber>
      requires THRESHOLD <=Int EXTEND_TO   // input is valid
       andBool SEQ <=Int LIVE_UNTIL        // entry is still alive

  // An invalid threshold or an expired instance leaves nothing to extend. Fail
  // the host call the way `extendContractDataTtl-err` fails the data-entry case,
  // rather than getting stuck: a stuck interpreter surfaces as an opaque node
  // error with no position, while a thrown error is a debuggable host trap.
    rule [extendContractTtl-err]:
        <instrs> extendContractTtl(_CONTRACT) => #throw(ErrStorage, InvalidAction) ... </instrs>
        <hostStack> U32(_THRESHOLD) : U32(_EXTEND_TO) : S => S </hostStack>
      [owise]

    syntax Int ::= extendedLiveUntil(Int, Int, Int, Int)    [function, total]
 // -----------------------------------------------------------------------------------
    rule extendedLiveUntil(SEQ, LIVE_UNTIL, THRESHOLD, EXTEND_TO)
      => minInt( SEQ +Int EXTEND_TO , maxLiveUntil(SEQ) )
      requires LIVE_UNTIL -Int SEQ <=Int THRESHOLD            // CURRENT_TTL <= THRESHOLD
       andBool LIVE_UNTIL          <Int  SEQ +Int EXTEND_TO   // LIVE_UNTIL  <  NEW_LIVE_UNTIL

    rule extendedLiveUntil(_, LIVE_UNTIL, _, _) => LIVE_UNTIL
      [owise]

    syntax InternalInstr ::= extendContractCodeTtl(ContractId)   [symbol(extendContractCodeTtl)]
 // --------------------------------------------------------------------------------------------
    rule [extendContractCodeTtl]:
        <instrs> extendContractCodeTtl(CONTRACT) => extendCodeTtl(HASH) ... </instrs>
        <contract>
          <contractId> CONTRACT </contractId>
          <contractExecutable> Wasm(HASH) </contractExecutable>
          ...
        </contract>

  // If the TTL for the contract code is less than `THRESHOLD`, update contractLiveUntil
  //    where TTL is defined as LIVE_UNTIL - SEQ.
    syntax InternalInstr ::= extendCodeTtl(Bytes)   [symbol(extendCodeTtl)]
 // -------------------------------------------------------------------------------
    rule [extendCodeTtl]:
        <instrs> extendCodeTtl(HASH) => .K ... </instrs>
        <hostStack> U32(THRESHOLD) : U32(EXTEND_TO) : S => S </hostStack>
        <contractCode>
          <codeHash> HASH </codeHash>
          <codeLiveUntil> LIVE_UNTIL
                       => extendedLiveUntil(SEQ, LIVE_UNTIL, THRESHOLD, EXTEND_TO)
          </codeLiveUntil>
          ...
        </contractCode>
        <ledgerSequenceNumber> SEQ </ledgerSequenceNumber>
      requires THRESHOLD <=Int EXTEND_TO   // input is valid
       andBool SEQ <=Int LIVE_UNTIL        // entry is still alive

    rule [extendCodeTtl-err]:
        <instrs> extendCodeTtl(_HASH) => #throw(ErrStorage, InvalidAction) ... </instrs>
        <hostStack> U32(_THRESHOLD) : U32(_EXTEND_TO) : S => S </hostStack>
      [owise]

```

## get_max_live_until_ledger

The last ledger an entry created now can live to, inclusive. This is a context
host function (`x.8`), but it lives here with the other TTL rules because that
is where `maxLiveUntil` and the max-entry-TTL constant are defined.

```k
    rule [hostfun-get-max-live-until-ledger]:
        <instrs> hostCall ( "x" , "8" , [ .ValTypes ] -> [ i64  .ValTypes ] )
              => toSmall(U32(maxLiveUntil(SEQ_NUM)))
                 ...
        </instrs>
        <locals> .Map </locals>
        <ledgerSequenceNumber> SEQ_NUM </ledgerSequenceNumber>
```

## Helpers

```k
    syntax StorageType ::= Int2StorageType(Int)   [function, total]
 // -------------------------------------------------------------------------------
    rule Int2StorageType(0) => #temporary
    rule Int2StorageType(1) => #persistent
    rule Int2StorageType(_) => #instance      [owise]

    syntax Bool ::= Int2StorageTypeValid(Int)   [function, total]
 // ------------------------------------------------------------
    rule Int2StorageTypeValid(I) => 0 <=Int I andBool I <=Int 2

  // make these values variable
    syntax Int ::= minEntryTtl(Durability)   [function, total]
                 | "#maxEntryTtl"            [macro]
 // -------------------------------------------------
    rule minEntryTtl(#temporary)  => 16 
    rule minEntryTtl(#persistent) => 4096
    rule #maxEntryTtl             => 6312000

    syntax Int ::= minLiveUntil(Durability, Int)   [function, total]
                 | maxLiveUntil(Int)               [function, total]
 // -----------------------------------------------------------------------
    rule minLiveUntil(DUR, SEQ) => SEQ +Int minEntryTtl(DUR) -Int 1
    rule maxLiveUntil(SEQ)      => SEQ +Int #maxEntryTtl -Int 1
    
    // Executable tags have protocol-enforced storage invariants.
    syntax Bool ::= isExecutableTagKey(ScVal) [function, total]
    rule isExecutableTagKey(ScExecutableTag(_)) => true
    rule isExecutableTagKey(_) => false [owise]

    syntax InternalInstr ::= validatePutContractData(StorageType)
                           | validateTagHash(Bytes)
                           | "validateDelContractData"

    rule <instrs> validatePutContractData(_) => .K ... </instrs>
         <hostStack> KEY : _VAL : _S </hostStack>
      requires notBool isExecutableTagKey(KEY)

    rule <instrs> validatePutContractData(T) => #throw(ErrStorage, InvalidInput) ... </instrs>
         <hostStack> ScExecutableTag(_) : _VAL : _S </hostStack>
      requires T =/=K #persistent

    rule <instrs> validatePutContractData(#persistent) => validateTagHash(HASH) ... </instrs>
         <hostStack> ScExecutableTag(_) : ScBytes(HASH) : _S </hostStack>

    rule <instrs> validatePutContractData(#persistent) => #throw(ErrStorage, InvalidInput) ... </instrs>
         <hostStack> ScExecutableTag(_) : _VAL : _S </hostStack>
      [owise]

    rule <instrs> validateTagHash(HASH) => #throw(ErrObject, UnexpectedSize) ... </instrs>
      requires lengthBytes(HASH) =/=Int 32
    rule <instrs> validateTagHash(HASH) => .K ... </instrs>
         <contractCode> <codeHash> HASH </codeHash> ... </contractCode>
      requires lengthBytes(HASH) ==Int 32
    rule <instrs> validateTagHash(_) => #throw(ErrStorage, MissingValue) ... </instrs> [owise]

    rule <instrs> validateDelContractData => #throw(ErrStorage, InvalidAction) ... </instrs>
         <hostStack> ScExecutableTag(_) : _S </hostStack>
    rule <instrs> validateDelContractData => .K ... </instrs>
         <hostStack> KEY : _S </hostStack>
      requires notBool isExecutableTagKey(KEY)

    rule [getContractData-missing]:
        <instrs> getContractData(_) => #throw(ErrStorage, MissingValue) ... </instrs> [owise]

    rule [hostfun-create-executable-tag]:
        <instrs> hostCallAux("l", "h") => allocObject(ScExecutableTag(TAG)) ~> returnHostVal ... </instrs>
        <hostStack> ScString(TAG) : S => S </hostStack>

    rule [hostfun-create-executable-tag-type]:
        <instrs> hostCallAux("l", "h") => #throw(ErrValue, UnexpectedType) ... </instrs> [owise]

    // Komet's existing authorization assumption is unchanged: deployer auth is
    // not modelled. IDs, executable checks, constructor execution and rollback are.
    rule [hostfun-create-contract-with-constructor]:
        <instrs> hostCallAux("l", "e")
              => createContractInput(DEPLOYER, Wasm(HASH), SALT, ARGS) ... </instrs>
        <hostStack> ScAddress(DEPLOYER) : ScBytes(HASH) : ScBytes(SALT) : ScVec(ARGS) : S => S </hostStack>

    rule [hostfun-create-external-ref-contract]:
        <instrs> hostCallAux("l", "i")
              => createContractInput(DEPLOYER, ExternalRef(OWNER, TAG), SALT, ARGS) ... </instrs>
        <hostStack> ScAddress(DEPLOYER) : ScAddress(OWNER) : ScExecutableTag(TAG)
                 : ScBytes(SALT) : ScVec(ARGS) : S => S </hostStack>

    rule [hostfun-create-contract-type]:
        <instrs> hostCallAux("l", FN) => #throw(ErrValue, UnexpectedType) ... </instrs>
      requires FN ==String "e" orBool FN ==String "i"
      [owise]

    syntax Bool ::= plainAddress(Address) [function, total]
    rule plainAddress(Account(A)) => lengthBytes(A) ==Int 32
    rule plainAddress(Contract(A)) => lengthBytes(A) ==Int 32
    rule plainAddress(_) => false [owise]

    syntax Bytes ::= deploymentAddressXdr(Address) [function, total]
    rule deploymentAddressXdr(Account(A)) => Int2Bytes(4, 0, BE) +Bytes Int2Bytes(4, 0, BE) +Bytes A
    rule deploymentAddressXdr(Contract(A)) => Int2Bytes(4, 1, BE) +Bytes A
    rule deploymentAddressXdr(_) => .Bytes [owise]

    syntax ContractId ::= deployedContractId(Bytes, Address, Bytes) [function, total]
    rule deployedContractId(NETWORK, DEPLOYER, SALT)
      => Contract(#sha256(Int2Bytes(4, 8, BE) +Bytes NETWORK +Bytes Int2Bytes(4, 0, BE)
                          +Bytes deploymentAddressXdr(DEPLOYER) +Bytes SALT))

    syntax InternalInstr ::= createContractInput(Address, ContractExecutable, Bytes, List)
    rule [createContractInput]:
        <instrs> createContractInput(DEPLOYER, EXEC, SALT, ARGS)
              => #waitCommands ~> returnCallResult ... </instrs>
        <callee> FROM </callee>
        <ledgerNetworkId> NETWORK </ledgerNetworkId>
        <k> (.K => prepareCreation(FROM, deployedContractId(NETWORK, DEPLOYER, SALT), EXEC, ARGS)) ... </k>
      requires plainAddress(DEPLOYER) andBool lengthBytes(SALT) ==Int 32 andBool lengthBytes(NETWORK) ==Int 32

    rule [createContractInput-invalid]:
        <instrs> createContractInput(_, _, _, _) => #throw(ErrObject, UnexpectedSize) ... </instrs> [owise]

    syntax InternalCmd ::= prepareCreation(Address, ContractId, ContractExecutable, List)
                         | createContractChecked(Address, ContractId, ContractExecutable, List, Int)
                         | invokeConstructor(Address, ContractId, List, Int)
                         | finishCreation(ContractId)

    rule [prepareCreation-duplicate]:
        <k> prepareCreation(_, ID, _, _) => pushStack(Error(ErrStorage, ExistingValue)) ... </k>
        <contract> <contractId> ID </contractId> ... </contract>
      [priority(40)]

    rule [prepareCreation-wasm]:
        <k> prepareCreation(FROM, ID, Wasm(HASH), ARGS)
         => createContractChecked(FROM, ID, Wasm(HASH), ARGS, PROTO) ... </k>
        <contractCode> <codeHash> HASH </codeHash> <codeProtocol> PROTO </codeProtocol> ... </contractCode>
      requires lengthBytes(HASH) ==Int 32

    rule [prepareCreation-bad-hash]:
        <k> prepareCreation(_, _, Wasm(HASH), _) => pushStack(Error(ErrObject, UnexpectedSize)) ... </k>
      requires lengthBytes(HASH) =/=Int 32
      [priority(30)]

    rule [prepareCreation-reference]:
        <k> prepareCreation(FROM, ID, ExternalRef(OWNER, TAG), ARGS)
         => createContractChecked(FROM, ID, ExternalRef(OWNER, TAG), ARGS, PROTO) ... </k>
        <contractData> ... #skey(OWNER, #persistent, ScExecutableTag(TAG)) |-> #sval(ScBytes(HASH), _) ... </contractData>
        <contractCode> <codeHash> HASH </codeHash> <codeProtocol> PROTO </codeProtocol> ... </contractCode>
      requires plainAddress(OWNER) andBool lengthBytes(HASH) ==Int 32

    rule [prepareCreation-missing]:
        <k> prepareCreation(_, _, _, _) => pushStack(Error(ErrStorage, MissingValue)) ... </k> [owise]

    rule [createContractChecked-duplicate]:
        <k> createContractChecked(_, ID, _, _, _) => pushStack(Error(ErrStorage, ExistingValue)) ... </k>
        <contract> <contractId> ID </contractId> ... </contract>

    rule [createContractChecked-new]:
        <k> createContractChecked(FROM, ID, EXEC, ARGS, PROTO)
         => pushWorldState ~> insertContract(ID, EXEC)
         ~> invokeConstructor(FROM, ID, ARGS, PROTO) ~> finishCreation(ID) ... </k>
      [owise]

    syntax InternalCmd ::= insertContract(ContractId, ContractExecutable)
    rule [insertContract]:
        <k> insertContract(ID, EXEC) => .K ... </k>
        (.Bag => <contract>
          <contractId> ID </contractId>
          <contractExecutable> EXEC </contractExecutable>
          <contractLiveUntil> minLiveUntil(#persistent, SEQ) </contractLiveUntil>
          ...
        </contract>)
        <ledgerSequenceNumber> SEQ </ledgerSequenceNumber>

    rule [invokeConstructor-legacy-empty]:
        <k> invokeConstructor(_, _, .List, PROTO) => pushStack(Void) ... </k>
      requires PROTO <Int 22
    rule [invokeConstructor-legacy-arguments]:
        <k> invokeConstructor(_, _, ARGS, PROTO) => pushStack(Error(ErrContext, InvalidAction)) ... </k>
      requires PROTO <Int 22 andBool size(ARGS) >Int 0
    rule [invokeConstructor]:
        <k> invokeConstructor(FROM, ID, ARGS, PROTO) => callContract(FROM, ID, "__constructor", ARGS) ... </k>
      requires PROTO >=Int 22

    rule [finishCreation-success]:
        <k> finishCreation(ID) => dropWorldState ... </k>
        <hostStack> Void : S => ScAddress(ID) : S </hostStack>
    rule [finishCreation-error]:
        <k> finishCreation(_) => popWorldState ... </k>
        <hostStack> Error(ET, CODE) : S
                 => (#if isRecoverable(ET, CODE) #then Error(ErrContext, InvalidAction) #else Error(ET, CODE) #fi) : S </hostStack>
    rule [finishCreation-nonvoid]:
        <k> finishCreation(_) => popWorldState ... </k>
        <hostStack> _RES:ScVal : S => Error(ErrValue, UnexpectedType) : S </hostStack>
      [owise]

    rule [extendContractCodeTtl-reference]:
        <instrs> extendContractCodeTtl(CONTRACT)
              => pushStack(ScExecutableTag(TAG)) ~> extendContractDataTtl(OWNER, #persistent)
              ~> pushStack(U32(EXTEND_TO)) ~> pushStack(U32(THRESHOLD)) ~> extendCodeTtl(HASH) ... </instrs>
        <hostStack> U32(THRESHOLD) : U32(EXTEND_TO) : _S </hostStack>
        <contract> <contractId> CONTRACT </contractId> <contractExecutable> ExternalRef(OWNER, TAG) </contractExecutable> ... </contract>
        <contractData> ... #skey(OWNER, #persistent, ScExecutableTag(TAG)) |-> #sval(ScBytes(HASH), _) ... </contractData>

    rule [extendContractCodeTtl-asset]:
        <instrs> extendContractCodeTtl(CONTRACT) => .K ... </instrs>
        <hostStack> _THRESHOLD : _EXTEND_TO : S => S </hostStack>
        <contract> <contractId> CONTRACT </contractId> <contractExecutable> StellarAsset </contractExecutable> ... </contract>

    rule [extendContractCodeTtl-missing]:
        <instrs> extendContractCodeTtl(_) => #throw(ErrStorage, MissingValue) ... </instrs> [owise]

    rule [hostfun-l-e-checked-inputs]:
        <instrs> hostCall("l", "e", [ i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => loadArgs(4) ~> hostCallAux("l", "e") ... </instrs>
        <locals> 0 |-> <i64> V0 1 |-> <i64> V1 2 |-> <i64> V2 3 |-> <i64> V3 </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires hostTypedRef(HostVal(V0), 77, OBJS, RELS)
       andBool hostTypedRef(HostVal(V1), 72, OBJS, RELS)
       andBool hostTypedRef(HostVal(V2), 72, OBJS, RELS)
       andBool hostTypedRef(HostVal(V3), 75, OBJS, RELS)

    rule [hostfun-l-e-invalid-inputs]:
        <instrs> hostCall("l", "e", [ i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
      [priority(60)]

    rule [hostfun-l-h-checked-inputs]:
        <instrs> hostCall("l", "h", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => loadArgs(1) ~> hostCallAux("l", "h") ... </instrs>
        <locals> 0 |-> <i64> V0 </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires hostTypedRef(HostVal(V0), 73, OBJS, RELS)

    rule [hostfun-l-h-invalid-inputs]:
        <instrs> hostCall("l", "h", [ i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
      [priority(60)]

    rule [hostfun-l-i-checked-inputs]:
        <instrs> hostCall("l", "i", [ i64 i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => loadArgs(5) ~> hostCallAux("l", "i") ... </instrs>
        <locals> 0 |-> <i64> V0 1 |-> <i64> V1 2 |-> <i64> V2 3 |-> <i64> V3 4 |-> <i64> V4 </locals>
        <hostObjects> OBJS </hostObjects>
        <relativeObjects> RELS </relativeObjects>
      requires hostTypedRef(HostVal(V0), 77, OBJS, RELS)
       andBool hostTypedRef(HostVal(V1), 77, OBJS, RELS)
       andBool hostTypedRef(HostVal(V2), 79, OBJS, RELS)
       andBool hostTypedRef(HostVal(V3), 72, OBJS, RELS)
       andBool hostTypedRef(HostVal(V4), 75, OBJS, RELS)

    rule [hostfun-l-i-invalid-inputs]:
        <instrs> hostCall("l", "i", [ i64 i64 i64 i64 i64 .ValTypes ] -> [ i64 .ValTypes ])
              => #throw(ErrValue, InvalidInput) ... </instrs>
      [priority(60)]

endmodule
```