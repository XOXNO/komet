# Borrow-double proof provenance and Linux reconstruction

This branch preserves the source selected by the native Komet
`test_borrow_double` proof completed on 2026-10-07. The original proof covers
fixed-factor borrow-index doubling, not the whole lending protocol. Linux must
rebuild native tools and compiled semantics; no cache, review-folder archive,
Mac binary, or Nix store output is published here.

## Source and version pins

| Component | Pin |
|---|---|
| Existing local Komet branch, preserved as-is | `XOXNO/komet`, `codex/borrow-index-sat-fast-path`, `ba813e1463a180ebcc4903658736ccb84755559a` |
| Exact Komet semantics and runner | `XOXNO/komet`, source commit `0593a6841c591b6f4c457c3a57a8abf3091ec411` |
| Vendored selected pyk overlay | Komet commit `d56a4ffb1e13bfa028aaafaab81481da0ad135f8`, base kframework/pyk `7.1.337` |
| K compiler | `v7.1.337`, Git revision `4a46d1231473b599c699160132fd6e76a5c46406` |
| Original K Nix path | `/nix/store/aqjgfc96ra0v1drpil3jlx23frcz5nrb-k-7.1.337-4a46d1231473b599c699160132fd6e76a5c46406` |
| Z3 | `4.13.4` |
| Python | `3.10.14` |
| pykwasm | `0.1.155`, semantics revision `bd5cbe7bfb3aafbeb4740884fed905394b542320` in `XOXNO/wasm-semantics` |
| Original installed komet metadata | `0.1.77`; actual imported source is identified by the hashes below |
| Patched backend | `XOXNO/haskell-backend`, branch `proof/booster-v6-compact-rpc`, commit `ba6bac8f48c0a830f93efc9568e1fbebaa04f732` |
| Backend version / build | `0.1.155`, original name `hs-backend-booster-0.1.155-v6-compact-rpc`, aarch64-darwin |
| Stellar CLI | `28.0.0` |
| Rust | `1.95.0` |
| Proof-artifact repository | `XOXNO/rs-lending-xlm`, `3997233f27faa20df63de69c8e79cfad867c1e91` on `codex/komet` |
| Harness source revision | `03657edf95ee9413f4aa28421c536f1c8363bec2` |

The source project's package metadata currently says `0.1.89`; it does not
identify the original Nix environment's imported source. The source hashes are
authoritative. All 44 non-bytecode files under the selected
`komet-canonical-inputs/src` match this branch. Only `proof.py` required a further
copy after the local semantics/test changes; there are no other differences.
All 13 Wasm semantics files in the selected cache match the pinned KWasm base.
Komet excludes the inherited optional `KWASM-LEMMAS` module.

## Original compiled inputs

The selected `KDIST_DIR` name is
`xor-range-candidate/cache/kdist-0d7b9c5`, under the historical
`borrow-goal-20261002` artifacts. Preserve this name as provenance; use a fresh
cache when compiling on Linux.

| Original input | SHA-256 |
|---|---|
| `src/komet/kdist/soroban-semantics/komet-lemmas.md` | `2ddebe516fe9b93c95e0ecaa1734b9226917fefebfbe44c7f77ee8bd855853c4` |
| `src/komet/proof.py` | `ac43e6cafd049c505f81b5e363968c509d656de5c9d57ab81c1eea091654a8e2` |
| `soroban-semantics/haskell/definition.kore` | `740936b5bb1978b96904325ae83224c83688c65a7b543a5163eca4ba6e882db4` |
| `soroban-semantics/llvm-library/definition.kore` | `8616fe0a829efdbb961f19abf747e522cb74cb8b053cb277af37b3254d5ce5ed` |
| `soroban-semantics/llvm-library/interpreter.dylib` | `671978dcfb985fcc6161a7cff6f1895525463b39127ec6998400edff00257280` |
| Original Booster executable | `0eda4843ca9302027925903ee3006d3f5143b02c81e590d9af2c54709dd5e8bf` |
| Proved Wasm | `099e7e12701d31576386154e93ffe1c1b3afe9aa981e62a59f291bf442820073` |

Linux compilation will produce different paths and native hashes, including
`interpreter.so`. Do not edit archived `inputs.json` to resume its graph on the
rebuilt runtime. Start fresh proof directories.

## Retained and omitted JSON records

`positive/` and `negative/` contain unchanged command, process, and artifact
checks from the final native runs. `positive/native-apr-check.json` retains the
final graph check. Each file is below 1 MB and is also present inside the
committed lending proof archive. Historical absolute paths are provenance, not
portable commands.

The requested full manifests exceed the 1 MB publication limit and are omitted:

| Original file | Bytes | SHA-256 |
|---|---:|---|
| `xor-range-candidate/inputs-before.json` | 4710130 | `2ed0962d9bf670ba3480dce21e614aace6a48ea1d86e0bc40cfb99a3413eca6f` |
| `xor-range-candidate/inherited-inputs.json` | 3289536 | `19d682747ee3b06b4343632e4d0dbbb43435a9c0acabd5b86ab4d1d8d36aa6a4` |
| Final positive `runtime.json` | 2022449 | `3349713b9f95e010dfe8cf090b8f7368ce7e289d8ec7322e7c5ef66aa32555fa` |
| Final negative `runtime.json` | 2012350 | `0ec84663b66ca6f3903dc86cd8ad446572fab2179a3d26dbf7223eea3e0cb227` |

These files and all original artifacts remain local and unchanged.

## Linux source build

Clone this Komet branch and the pinned backend. Check out Komet
`d56a4ffb1e13bfa028aaafaab81481da0ad135f8` for a fixed runtime source including
the overlay, and backend `ba6bac8f48c0a830f93efc9568e1fbebaa04f732`.

Build the backend through its locked flake:

```sh
cd /path/to/haskell-backend
nix build --no-write-lock-file .#kore-rpc-booster --out-link result-booster
./result-booster/bin/kore-rpc-booster --version
nix develop --no-write-lock-file --command z3 --version
```

The flake builds the same committed package sources with GHC 9.6.5 and wraps
Booster with Z3 4.13.4. Its normal build disables package tests and does not run
the standalone `MapKeyCheck.hs` fixture. The copied
`nix/booster-v6-compact-rpc.nix` preserves the exact historical Darwin recipe;
its external relative references are not a standalone Linux build entry point.

With K 7.1.337 and uv available, install the locked Python dependencies:

```sh
cd /path/to/komet
uv sync --locked --python 3.10.14
. .venv/bin/activate
kompile --version
python --version
```

Apply and verify the full-package `PYTHONPATH` overlay using
[vendor/pyk-overlay/README.md](../vendor/pyk-overlay/README.md). Keep that
`PYTHONPATH` in this shell. Invoke environment commands directly; another
synchronizing `uv run` or installation can select a different package.

Select the separately built patched backend, with the original flags:

```sh
export BORROW_DOUBLE_BOOSTER=/absolute/path/to/haskell-backend/result-booster/bin/kore-rpc-booster
BORROW_DOUBLE_BIN="$(mktemp -d)"
cat > "$BORROW_DOUBLE_BIN/kore-rpc-booster" <<'SH'
#!/bin/sh
exec "${BORROW_DOUBLE_BOOSTER:?set the patched Booster executable}" "$@" \
  --equation-max-local-steps 32 --no-fallback-simplify \
  --no-post-exec-simplify --smt-retry-limit 3
SH
chmod +x "$BORROW_DOUBLE_BIN/kore-rpc-booster"
export PATH="$BORROW_DOUBLE_BIN:$PATH"
unset KDIST_DIR APPLE_SILICON
export XDG_CACHE_HOME="$(mktemp -d)"
komet-kdist -v build -j2 'soroban-semantics.*'
python -m pytest -q src/tests/unit
python -m pytest -q src/tests/integration/test_symbolic_word_concat.py
```

The selected runner starts SMT queries at 5,000 ms. Keep the wrapper first on
`PATH` so K's bundled unpatched Booster is not selected.

## Fresh proof inputs

The pinned lending checkout has the exact Wasm, extra module, graph archive,
and checker at `komet/pool-math/proofs/borrow-double`. Its README contains the
full original claim, negative control, and harness build commands. With Stellar
CLI 28.0.0 and Rust 1.95.0, any rebuilt Wasm must match the hash above before use.

Validate the saved artifacts, then extract the proved Wasm into a new directory:

```sh
export BORROW_DOUBLE_INPUTS=/absolute/path/to/rs-lending-xlm/komet/pool-math/proofs/borrow-double
(cd "$BORROW_DOUBLE_INPUTS" && sha256sum -c SHA256SUMS && python verify.py)
export BORROW_DOUBLE_FRESH="$(mktemp -d)"
tar -xzf "$BORROW_DOUBLE_INPUTS/native-proof.tar.gz" \
  -C "$BORROW_DOUBLE_FRESH" wasm/pool_math_proof.wasm
printf '%s  %s\n' \
  099e7e12701d31576386154e93ffe1c1b3afe9aa981e62a59f291bf442820073 \
  "$BORROW_DOUBLE_FRESH/wasm/pool_math_proof.wasm" | sha256sum -c -

komet prove run --always-allocate \
  --wasm "$BORROW_DOUBLE_FRESH/wasm/pool_math_proof.wasm" \
  --id test_borrow_double \
  --extra-module "$BORROW_DOUBLE_INPUTS/double-cli.k:SIGNED-DISTRIBUTE-COMPLEMENT-NEGATIVE-PACK64-DOUBLE-RAY-SIGNED-DECODER-FLOOR-EQUALITY-LOW-WORD-SIGNED64-SIGN-FIXED64-XOR" \
  --proof-dir "$BORROW_DOUBLE_FRESH/positive"
```

Run `test_borrow_double_wrong` separately into a different fresh directory; it
must fail its Boolean assertion. A crash, timeout, parser failure, or unknown
result is not a successful control. Positive completion requires native APR
`PASSED` without pending/failing/stuck leaves, admissions, bounds, or an empty
initial domain. Retain new graphs, logs, manifests, and Linux artifact hashes.
The archived checker validates saved graphs and hashes; it is not independent
certificate replay. Linux compilation and a fresh proof remain unverified.
