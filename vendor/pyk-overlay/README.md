# Exact borrow-double pyk overlay

Base: `kframework` / pyk **7.1.337**, from K commit
`4a46d1231473b599c699160132fd6e76a5c46406`.

These two files are unchanged copies from the proof-selected
`pyk-fast-subsumption` package. `LICENSE.md` is pyk's upstream BSD license.

| Path under `pyk/` | Original upstream SHA-256 | Selected SHA-256 |
|---|---|---|
| `konvert/_kast_to_kore.py` | `ddc9aa9abff1b180cf8276375647469b83cfd3cba5f385cbd899e0529431d47f` | `fdd855b4d4280f8739ffb5963f3d4997756ec44585f4b23ae94cd85f5a75463a` |
| `proof/reachability.py` | `dfc1f86ef0e8cae44c5833efd4b0d613ee90ff4d7747e0663d3c575b0191fd30` | `057fcc12b91f8f7ce355c74626e79df83b6f6623ba8772c2e9813588fd3ef3dd` |

- `_kast_to_kore.py`: convert the empty `preserves-definedness` attribute.
- `reachability.py`: preserve successful empty substitutions in fast
  subsumption; the specific `retry limit is 0` SMT error establishes no cover,
  while other errors propagate.

## Use through PYTHONPATH

The proof prepended a complete copied pyk package to `PYTHONPATH`. This vendor
directory contains only its two changed files. Prepending this partial directory
alone cannot override an installed regular Python package. Assemble the full
installed 7.1.337 package first, apply the two files, then prepend that copy.

Run from this Komet checkout in its Python 3.10 environment, after installing
the locked dependencies. Start without an earlier pyk override:

```sh
unset PYTHONPATH
BORROW_DOUBLE_PYK_BASE="$(python -c 'from importlib.metadata import version; from pathlib import Path; import pyk; assert version("kframework") == "7.1.337"; print(Path(pyk.__file__).resolve().parent)')"
printf '%s  %s\n' \
  ddc9aa9abff1b180cf8276375647469b83cfd3cba5f385cbd899e0529431d47f \
  "$BORROW_DOUBLE_PYK_BASE/konvert/_kast_to_kore.py" \
  dfc1f86ef0e8cae44c5833efd4b0d613ee90ff4d7747e0663d3c575b0191fd30 \
  "$BORROW_DOUBLE_PYK_BASE/proof/reachability.py" | sha256sum -c -

export BORROW_DOUBLE_PYK_OVERLAY="$(mktemp -d)"
cp -R "$BORROW_DOUBLE_PYK_BASE" "$BORROW_DOUBLE_PYK_OVERLAY/pyk"
chmod -R u+w "$BORROW_DOUBLE_PYK_OVERLAY/pyk"
cp -R vendor/pyk-overlay/pyk/. "$BORROW_DOUBLE_PYK_OVERLAY/pyk/"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$BORROW_DOUBLE_PYK_OVERLAY"

python - <<'PY'
from hashlib import sha256
from pathlib import Path
from pyk.konvert import _kast_to_kore
from pyk.proof import reachability

for module, expected in [
    (_kast_to_kore, 'fdd855b4d4280f8739ffb5963f3d4997756ec44585f4b23ae94cd85f5a75463a'),
    (reachability, '057fcc12b91f8f7ce355c74626e79df83b6f6623ba8772c2e9813588fd3ef3dd'),
]:
    path = Path(module.__file__)
    assert sha256(path.read_bytes()).hexdigest() == expected, path
    print(path)
PY
```

Keep this `PYTHONPATH` for compilation, proof runs, and the Komet subprocesses.
Use the environment's commands directly; do not replace the selected package
with another installation. No pyk fork is needed.
