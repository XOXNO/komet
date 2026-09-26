# SDK 28 host support

This fork adds models for eleven host imports used by Soroban SDK 28, targeting
`soroban-env-host` 28.0.2 behavior. The integration workspace and
test-project template pin `soroban-sdk` 28.0.0. This is a scoped extension of
Komet's host model, not complete implementation of every protocol-28 import.

## Added imports

An import such as `m.b` means Wasm module `"m"`, function `"b"`.

| Import | Host function | Modeled behavior |
|---|---|---|
| `b._` | `serialize_to_bytes` | ScVal XDR encoding, including conversion and size limits |
| `b.0` | `deserialize_from_bytes` | ScVal XDR decoding and malformed-input checks |
| `b.g` | `string_copy_to_linear_memory` | Byte copies with source, destination and overflow checks |
| `b.k` | `string_len` | String length in bytes |
| `c.1` | `compute_hash_keccak256` | Keccak-256 digest computation |
| `m.b` | `sparse_map_new_from_linear_memory` | Ordered Symbol keys; Void entries omitted after validation |
| `m.c` | `sparse_map_unpack_to_linear_memory` | Ordered byte queries; missing keys written as Void |
| `a.6` | `get_address_executable` | Account, Wasm and Stellar Asset executable descriptions; external-reference resolution |
| `l.e` | `create_contract_with_constructor` | Contract-ID derivation, uploaded-code checks, constructor execution and rollback |
| `l.h` | `create_executable_tag` | Executable tags from strings |
| `l.i` | `create_external_ref_contract` | Deployment through an owner's persistent executable tag |

SHA-256 (`c._`, `compute_hash_sha256`) is also implemented to support contract-ID
derivation. The digest implementations compute outputs rather than returning
uninterpreted placeholders. Signature-verification imports are outside this change.

The [host modules](../src/komet/kdist/soroban-semantics/host/hostfuns.md) contain
these definitions and their error paths.

## Contract metadata

Contract loading reads interface metadata through `stellar contract info env-meta`.
It requires exactly one interface-version entry, an integer protocol from 0
through 28, and `pre_release = 0`; newer or prerelease interfaces are rejected.
Each uploaded contract retains its protocol, including child contracts.

That protocol controls constructor behavior: code predating protocol 22 skips
constructors and rejects constructor arguments; protocol-22+ code invokes
`__constructor`. A missing constructor is allowed only with no arguments.
Handwritten WAST fixtures default to protocol 28 and can select a protocol with
`uploadWasmWithProtocol(hash, module, protocol)`.

These metadata checks select modeled behavior. They do not imply that every
historical protocol rule or host import is implemented.

The binary frontend accepts the optional `DataCount` section emitted by the
SDK 28 toolchain. It checks uniqueness, placement, encoding and agreement with
the parsed data-segment count before translating the module. Only this metadata
section is removed from the in-memory input to the pinned parser; the source
Wasm, other sections, data bytes and instructions are preserved. Data segments
must use the implicit active memory-zero encoding. Passive and explicit-memory
data modes, unknown sections and unsupported instructions remain errors; this
does not add bulk-memory instruction support.

The adapter also repairs the pinned parser's `if/else` branch split: position
wrappers hid the real `else` delimiter, incorrectly placing both branches in
the then clause. The repair restores nested branch structure while retaining
instruction positions and result types. Binary regressions execute both
condition values through the concrete backend.

## Model boundaries

- **Authorization:** existing `require_auth` (`a.0`) and
  `authorize_as_curr_contract` (`a.3`) remain no-ops. Deployment also assumes
  deployer authorization. Tests or proofs using this model do not establish
  authorization correctness.
- **Events:** existing `contract_event` (`x.1`) remains a no-op. Event contents,
  validation and emitted logs are not verified.
- **Object handles:** existing imports can expose absolute host handles, while
  contract arguments use relative handles. The new argument checks accept
  known, correctly typed handles in either representation. A forged known
  absolute guest handle is therefore not distinguished from an existing
  import's result; this model does not verify that guest isolation boundary.
- **Memory exports:** the added memory operations require an export named
  `memory` that resolves to linear memory. KWasm's binary frontend retains export
  names and indices but discards export kinds. A function or global named
  `memory` with the same index as an unexported memory therefore cannot be
  distinguished from a real memory export by this model.
- **Wasm validation:** the underlying frontend is not a complete protocol-28
  validator. Added import signatures are checked when invoked, rather than on
  upload. Proofs assume modules also pass Stellar's native Wasm validation.
- **Budgets:** there is no complete Soroban CPU, memory-allocation or instruction
  cost model. Successful execution does not establish native budget feasibility.
  Explicit local limits, such as XDR recursion and encoded size, are still checked.

Proof conclusions apply to the implemented transitions and these assumptions.

## Symbolic validation status

The SDK 28 round-trip fixture passes concrete execution and fuzzing. Its symbolic
proof is not yet established: the default booster RPC disconnects during
execution, while a simple SDK 28 adder proof succeeds under the same semantics.
Treat the added models as experimental for symbolic workloads until this failure
is resolved. Concrete test results do not establish a formal proof.

## Run the checks

Use the repository's [development setup](../CONTRIBUTING.md#setup), including K,
Rust and the compatible Stellar CLI. From the repository root, build the semantics
and run a direct host fixture plus the SDK contract smoke test:

```sh
make kdist-build
uv run komet run src/tests/integration/data/sparse_map.wast
uv run komet test -C src/tests/integration/data/soroban/contracts/test_sdk28 \
  --id test_roundtrip --max-examples 1
uv run pytest src/tests/unit/test_protocol.py src/tests/unit/test_wasm.py
```

The SDK fixture exercises optional struct fields, storage, XDR and string copying.
One fuzzing example is a smoke check, not a proof. Other direct fixtures cover
XDR, strings, both hashes, invalid crypto arguments, deployment and added value
types. Run their concrete and tracing variants together with:

```sh
make test-integration TEST_ARGS='-k "test_run and (sparse_map or xdr or string_memory or crypto or sdk28)"'
```
