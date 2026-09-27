from itertools import product
from typing import TYPE_CHECKING

from pyk.kast.inner import KApply, KVariable, Subst
from pyk.kast.prelude.collections import list_of
from pyk.kast.prelude.utils import bytesToken, token

from komet.proof import simplify

if TYPE_CHECKING:
    from pyk.kast.inner import KInner


_SPARSE_CONS = '___SPARSE-BYTES-SYNTAX_SparseBytes_SBItemChunk_SparseBytes'
_SPARSE_NIL = '.List{"___SPARSE-BYTES-SYNTAX_SparseBytes_SBItemChunk_SparseBytes"}_SparseBytes'
_SPARSE_CHUNK = 'SBChunk(_)_SPARSE-BYTES-SYNTAX_SBItemChunk_SBItem'
_GET_RANGE = '#getRange(_,_,_)_WASM-DATA-COMMON_Int_SparseBytes_Int_Int'
_SET_RANGE = '#setRange(_,_,_,_)_WASM-DATA-COMMON_SparseBytes_SparseBytes_Int_Int_Int'


def _memory(data: bytes, zero_prefix: int = 0) -> KApply:
    result = KApply(_SPARSE_CONS, KApply(_SPARSE_CHUNK, KApply('SBItem:bytes', bytesToken(data))), KApply(_SPARSE_NIL))
    if zero_prefix:
        result = KApply(_SPARSE_CONS, KApply(_SPARSE_CHUNK, KApply('SBItem:empty', token(zero_prefix))), result)
    return result


def _read(memory: 'KInner', address: int, width: int) -> KApply:
    return KApply(_GET_RANGE, memory, token(address), token(width))


def _write(memory: 'KInner', address: int, value: 'KInner', width: int) -> KApply:
    return KApply(_SET_RANGE, memory, token(address), value, token(width))


def _model_write(memory: bytes, address: int, value: int, width: int) -> dict[int, int]:
    # Independent byte-addressed model: invalid writes do nothing; positive writes truncate.
    result = dict(enumerate(memory))
    if address >= 0 and value >= 0 and width > 0:
        for offset in range(width):
            result[address + offset] = (value // 256**offset) % 256
    return result


def _model_read(memory: dict[int, int], address: int, width: int) -> int:
    if address < 0 or width <= 0:
        return 0
    return sum(memory.get(address + offset, 0) * 256**offset for offset in range(width))


def test_symbolic_zero_mask() -> None:
    value = KVariable('X', 'Int')
    for left, right in [(value, token(0)), (token(0), value)]:
        assert simplify(KApply('_&Int_', left, right)) == token(0)


def test_symbolic_shift_mod_preserves_counterexample() -> None:
    # The retired KWASM lemma incorrectly reduced this expression to zero for every X.
    expression = KApply('_modInt_', KApply('_<<Int_', KVariable('X', 'Int'), token(3)), token(3))
    simplified = simplify(expression)
    assert simplified != token(0)
    # Re-evaluate both residues so replacing the symbolic term with either constant fails.
    for value, expected in [(0, 0), (1, 2)]:
        concrete = Subst({'X': token(value)}).apply(simplified)
        assert simplify(concrete) == token(expected)


def test_oracle_adjacent_write_cannot_change_zero_flag() -> None:
    # Exact memory/constraint shape from the false oracle branch at addresses 1048560/1048568.
    memory = _memory(bytes(8), zero_prefix=1048560)
    read = _read(_write(memory, 1048568, KVariable('ARG_0', 'Int'), 8), 1048560, 8)
    impossible = KApply('notBool_', KApply('_==Int_', token(0), KApply('boolToInt', KApply('_==Int_', read, token(1)))))
    assert simplify(impossible) == token(False)


def test_symbolic_disjoint_reads_in_both_directions() -> None:
    memory = KVariable('MEMORY', 'SparseBytes')
    value = KVariable('VALUE', 'Int')
    # Adjacent and separated ranges, with an entirely unconstrained stored value.
    cases = [(8, 8, 0, 8), (16, 8, 0, 8), (0, 8, 8, 8), (0, 8, 16, 8)]
    reads = [
        _read(_write(memory, address, value, width), read_address, read_width)
        for address, width, read_address, read_width in cases
    ]
    expected = [_read(memory, read_address, read_width) for _, _, read_address, read_width in cases]
    # Negative values and empty writes are no-ops even when nominal intervals overlap.
    reads += [_read(_write(memory, 4, token(-1), 8), 0, 8), _read(_write(memory, 4, value, 0), 0, 8)]
    expected += [_read(memory, 0, 8), _read(memory, 0, 8)]
    reads.append(_read(_write(memory, 4, value, 8), 6, 0))
    expected.append(token(0))
    # A nonempty overlap must retain its unconstrained write.
    overlapping = _read(_write(memory, 4, value, 8), 0, 8)
    reads.append(overlapping)
    expected.append(overlapping)
    assert simplify(list_of(reads)) == list_of(expected)


def test_disjoint_rules_against_finite_byte_model() -> None:
    # Every combination covers both directions, adjacency, empty intervals, and negative values.
    for memory, address, width, value, read_address, read_width in product(
        [bytes(6), bytes([0x21, 0x43, 0x65, 0x87, 0xA9, 0xCB])],
        range(6),
        range(4),
        [-1, 0, 1, 255, 256, 0xFEFEFE, 1 << 64],
        range(6),
        range(4),
    ):
        if read_address + read_width <= address or address + width <= read_address:
            before = _model_read(dict(enumerate(memory)), read_address, read_width)
            after = _model_read(_model_write(memory, address, value, width), read_address, read_width)
            assert after == before
    # Positive overlap really can change a read: disjointness is essential.
    assert _model_read(_model_write(bytes(4), 1, 0x0201, 2), 0, 2) == 0x0100
    assert _model_read(_model_write(bytes(4), 1, 0x0201, 2), 2, 2) == 0x02


def test_concrete_memory_semantics_against_byte_model() -> None:
    memory = bytes([0x21, 0x43, 0x65, 0x87, 0xA9, 0xCB])
    cases = list(product([0, 1, 2, 7], [0, 2], [-1, 0x03020100, 1 << 40], [0, 1, 2, 7], [0, 2]))
    # Include invalid addresses/widths, whose defining semantics are no-op writes or zero reads.
    cases += [(-1, 2, 1, 0, 2), (0, -1, 1, 0, 2), (0, 2, 1, -1, 2), (0, 2, 1, 0, -1)]
    reads = [
        _read(_write(_memory(memory), address, token(value), width), read_address, read_width)
        for address, width, value, read_address, read_width in cases
    ]
    expected = [
        token(_model_read(_model_write(memory, address, value, width), read_address, read_width))
        for address, width, value, read_address, read_width in cases
    ]
    # One backend session checks 196 concrete overlapping/disjoint reads against the independent model.
    assert simplify(list_of(reads)) == list_of(expected)
