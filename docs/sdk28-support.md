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

## Integer model repairs

The numeric host model now matches the checked cases for:

- Allocated `U256`/`I256` values use object tags 70/71, including small values
  and intermediate results under `--always-allocate`.
- Limb constructors return objects even for zero. Object-only limb accessors
  reject packed small integers and malformed object tags before argument
  decoding loses that distinction.
- Checked signed and unsigned add, subtract, multiply and divide reject
  overflow or zero divisors with the native `Object/ArithDomain` error.
  Signed division also rejects `I256::MIN / -1`.
- Signed Euclidean remainder returns a nonnegative result on its valid domain,
  but rejects both zero divisors and `I256::MIN % -1`, as the native host does.
- Integer byte constructors reject lengths other than 32 bytes with
  `Object/UnexpectedSize`.

The repair validation recorded 95 K integration checks: 49 concrete and 46
tracing checks. An independent replay of the numeric fixtures passed 89 cases
against `soroban-env-host` 28.0.2. These are checked examples and error paths,
not a universal equivalence proof of the model and native host.

## Symbolic arithmetic trust boundary

The optional inherited `KWASM-LEMMAS` module has been removed from
[`komet-lemmas.md`](../src/komet/kdist/soroban-semantics/komet-lemmas.md).
Review flagged nine identities there. Six negative-shift examples fall outside
K's declared defined domain and are not counted as established proof-soundness
defects. The other candidates concern modulus, signed right-shift and memory
writes. A real symbolic backend
reproduced the unsound simplification `(X << 3) mod 3 => 0`; at `X = 1`, the
correct remainder is `2`.

Freshly rebuilt definitions use the base KWasm/K arithmetic semantics and the
explicitly retained Soroban lemmas, without that optional optimization module.
Two independently reviewed rules preserve reads outside a written byte range,
with nonnegative address/width guards. A reviewed `X &Int 0 => 0` rule retains
the default definedness obligation; no `preserves-definedness` exemption is used.
Three further guarded rules establish nonnegative masked-word bounds and
unwrap values already within the requested byte width. They repair unresolved
i128 limb comparisons and memory reads without restricting contract inputs.
Seven focused backend regressions pass, including negative mask/bound cases,
word overflow, zero/negative widths and partial arithmetic operands. The exact
previously stopped half-up state simplifies under its original constraints.

Further reviewed normalization exposes word arithmetic to SMT: full masks become
Euclidean remainders, Boolean words become `if B then 1 else 0`, and signed i32/i64
casts become piecewise arithmetic only after establishing the unsigned-word range.
The inverse remainder-to-mask rule is removed. No contract-input bounds are added,
and partial operands retain their definedness obligations. Regressions cover signed
boundaries, invalid cast domains, negative integers, sparse masks and division by
zero, plus exact saved borrower branch and terminal constraints.

Constant nonnegative right shifts now use Euclidean division, including negative
integers. Unsigned conversion becomes piecewise arithmetic only within its declared
mixed signed/unsigned domain, `[-2^(w-1), 2^w)`. Four 64-bit limbs become a weighted
sum only when every limb lies in `[0, 2^64)`. Tests independently exercise each lower
and upper guard and preserve undefined partial operands. These rules close the
saved half-up error path using all 12 original constraints without new premises.

Before extending a state, APR now checks its complete normalized constraints with
a typed SMT query. Only an explicit `UnsatResult` makes that path vacuous. SAT and
Unknown continue through ordinary exploration; RPC errors propagate. The query
retains normalization's definedness predicates and uses neither the target nor
the desired result. A constraints-only query can establish a contradiction but
does not certify that the full configuration has a feasible execution.

The current rebuild passed 31 focused arithmetic/path/module checks, six existing
symbolic regressions and 49 concrete integration checks. The exact infeasible
borrower branch/terminal fixtures and the saved half-up error path close;
the initial and feasible predecessor fixtures remain open. These local checks do
not establish a completed universal pool-property proof.

Removing the whole import avoids trusting the remaining unreviewed identities
in that module. It may make proofs slower; it does not justify weakening claims.

**Older arithmetic proofs are provisional and must be rerun.** The earlier
95 integer-model checks above were also rerun after removal and the guarded
memory rules; all passed. A dedicated symbolic regression rejects the original
modulus corruption and checks the replacement memory rules. No new general arithmetic
theorem is accepted from the replacement definitions yet. A previously passing
adder, isolated identity or concrete SDK round-trip does not establish that
arithmetic-bearing pool properties are proved. Compilation, fuzzing, a saved
checkpoint and a backend crash are not symbolic proof verdicts.

## Runtime and result integrity

On macOS, the Booster launcher interposes default worker-thread creation to
provide 64 MiB native stacks. This addresses recursive LLVM serialization that
could terminate Booster with `SIGBUS`; raising the main process stack alone did
not repair it. Explicit thread attributes are preserved. The workaround is
finite and changes execution resources, not the mathematical model. It does
not guarantee that every symbolic workload terminates.

The launcher builds `native_stack.c` with `xcrun clang` into a content-addressed
cache, then executes Booster with its original arguments. Xcode command-line
tools and a writable cache are required on macOS. The Python wheel includes
both the C source and launcher; source exports must retain those files too.

Saved proofs now record the actual claim, extra module, compiled Haskell/LLVM
definitions, native LLVM library and runtime `proof.py` fingerprints in
`inputs.json`. Resuming
with changed or unrecorded inputs is rejected. Checkpoints are written when
execution raises an exception or is interrupted; a checkpoint is not a proof.
Use fresh proof directories after changing Wasm, semantics or the proof runner.

Before APR advancement, including resumption of an already passed proof, the runner
rejects a syntactically bottom or marked-vacuous initial state and initial constraints
proved UNSAT. It checks the initial bottom/vacuous status again after advancement.
This prevents initial-state subsumption from accepting an empty-domain proof.
Infeasible child paths may still close after an independent UNSAT query. These
guards do not replace a separate witness for the intended initial domain.

Both contract proofs and raw proofs require `PASSED`; pending and failed
statuses propagate failure. Empty contract-test or raw-claim selections also
fail instead of returning success. Negative controls must reach the expected
assertion failure; a nonzero exit caused by a tool crash is inconclusive.

Runtime, resume and verdict validation currently passes 103 unit checks, including
explicit Unknown handling, backend errors, initial-vacuity CLI failure, resumed
initial Bottom, module selection and runner-source fingerprint changes.
These checks validate the tooling paths, not contract correctness.

## Run the checks

The recorded SDK 28 environment uses Stellar CLI 28.0.0, Rust 1.95.0, native K
and Python `kframework`/pyk 7.1.337, and KWasm 0.1.155. The older
[development setup](../CONTRIBUTING.md#setup) mentions Stellar CLI 23; use CLI 28
for these SDK 28 harnesses. `pyproject.toml` and `uv.lock` pin pyk 7.1.337;
`deps/k_release` and the nested Nix K input pin the same native K release.
KWasm remains 0.1.155. Normal `uv run` now uses the recorded pyk version without
a command-line package override.

From the repository root, with native K and its backend tools on `PATH`, build
fresh definitions after the lemma removal:

```sh
uv sync --locked --python 3.10
export XDG_CACHE_HOME="$PWD/.komet-cache"
if [ "$(uname -sm)" = 'Darwin arm64' ]; then export APPLE_SILICON=true; fi
uv run --locked komet-kdist -v build -j2 'soroban-semantics.*'
uv run --locked komet run src/tests/integration/data/sparse_map.wast
uv run --locked komet test \
  -C src/tests/integration/data/soroban/contracts/test_sdk28 \
  --id test_roundtrip --max-examples 1
uv run --locked pytest src/tests/unit
```

Keep that same cache and locked environment for later runs. These are reproduction
commands; this document does not claim a fresh post-removal run has completed.

The SDK fixture exercises optional struct fields, storage, XDR and string copying.
One fuzzing example is a smoke check, not a proof. Other direct fixtures cover
XDR, strings, both hashes, invalid crypto arguments, deployment and added value
types. Run their concrete and tracing variants together with:

```sh
uv run --locked pytest src/tests/integration \
  -k 'test_run and (sparse_map or xdr or string_memory or crypto or sdk28)'
uv run --locked pytest src/tests/integration \
  -k 'i256 or u256 or integer_abi'
```
