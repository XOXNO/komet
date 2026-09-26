from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from pyk.kast.inner import KApply, KInner
from pykwasm import kwasm_ast as wasm_ast
from pykwasm.wasm2kast import wasm2kast as legacy_wasm2kast
from wasm.exceptions import MalformedModule, ParseError  # type: ignore[import-untyped]
from wasm.instructions import Else, End, If, InstructionWithPos, Nop  # type: ignore[import-untyped]

from komet.wasm import _restore_if_branches, wasm2kast

HEADER = b'\x00asm\x01\x00\x00\x00'
TYPES = bytes.fromhex('01 04 01 60 00 00')
FUNCTIONS = bytes.fromhex('03 02 01 00')
MEMORY = bytes.fromhex('05 03 01 00 01')
CODE = bytes.fromhex('0a 07 01 05 00 41 0c 1a 0b')
DATA = bytes.fromhex('0b 09 01 00 41 00 0b 03 0c 01 01')
DATA_COUNT = bytes.fromhex('0c 01 01')
CUSTOM = bytes.fromhex('00 04 01 6e fe ff')


def _if_nodes(term: KInner) -> list[KApply]:
    found = []
    pending = [term]
    while pending:
        current = pending.pop()
        if isinstance(current, KApply):
            if current.label.name == 'aIf':
                found.append(current)
            pending.extend(reversed(current.args))
    return found


def test_if_else_preserves_branches_and_positions() -> None:
    # choose(x): if i64.eqz(x) then i64.const 1 else i64.const 0.
    wasm = Path(__file__).parents[1] / 'integration' / 'data' / 'if_else.wasm'
    [branch] = _if_nodes(wasm2kast(wasm.read_bytes()))
    assert branch.args[0] == wasm_ast.vec_type(wasm_ast.val_types([wasm_ast.i64]))
    assert branch.args[1] == wasm_ast.instrs([wasm_ast.INSTR_WITH_POS(wasm_ast.I64_CONST(1), 8, 2)])
    assert branch.args[2] == wasm_ast.instrs([wasm_ast.INSTR_WITH_POS(wasm_ast.I64_CONST(0), 11, 2)])


def test_nested_if_in_block_and_loop() -> None:
    body = bytes.fromhex('00 02 7e 03 7e 20 00 50 04 7e 42 01 05 20 00 50 04 7e 42 02 05 42 03 0b 0b 0b 0b 0b')
    code = bytes([10, len(body) + 2, 1, len(body)]) + body
    module = HEADER + bytes.fromhex('01 06 01 60 01 7e 01 7e') + FUNCTIONS + code
    outer, inner = _if_nodes(wasm2kast(module))
    assert outer.args[1] == wasm_ast.instrs([wasm_ast.INSTR_WITH_POS(wasm_ast.I64_CONST(1), 12, 2)])
    assert inner.args[1] == wasm_ast.instrs([wasm_ast.INSTR_WITH_POS(wasm_ast.I64_CONST(2), 20, 2)])
    assert inner.args[2] == wasm_ast.instrs([wasm_ast.INSTR_WITH_POS(wasm_ast.I64_CONST(3), 23, 2)])


def test_if_without_else_remains_unchanged() -> None:
    body = bytes.fromhex('00 41 01 04 40 01 0b 0b')
    code = bytes([10, len(body) + 2, 1, len(body)]) + body
    [branch] = _if_nodes(wasm2kast(HEADER + TYPES + FUNCTIONS + code))
    assert branch.args[1] == wasm_ast.instrs([wasm_ast.INSTR_WITH_POS(wasm_ast.NOP, 7, 1)])
    assert branch.args[2] == wasm_ast.instrs([])


@pytest.mark.parametrize('then_nop,else_nop', [(False, True), (True, False), (False, False)])
def test_empty_if_branches(then_nop: bool, else_nop: bool) -> None:
    then = b'\x01' if then_nop else b''
    otherwise = b'\x01' if else_nop else b''
    body = bytes.fromhex('00 41 01 04 40') + then + b'\x05' + otherwise + b'\x0b\x0b'
    code = bytes([10, len(body) + 2, 1, len(body)]) + body
    [branch] = _if_nodes(wasm2kast(HEADER + TYPES + FUNCTIONS + code))
    expected_then = [wasm_ast.INSTR_WITH_POS(wasm_ast.NOP, 7, 1)] if then_nop else []
    expected_else = [wasm_ast.INSTR_WITH_POS(wasm_ast.NOP, 8 + int(then_nop), 1)] if else_nop else []
    assert branch.args[1] == wasm_ast.instrs(expected_then)
    assert branch.args[2] == wasm_ast.instrs(expected_else)


def test_multiple_else_clauses_rejected() -> None:
    body = bytes.fromhex('00 41 01 04 40 05 05 0b 0b')
    code = bytes([10, len(body) + 2, 1, len(body)]) + body
    with pytest.raises(ParseError, match='multiple else clauses'):
        wasm2kast(HEADER + TYPES + FUNCTIONS + code)


def test_already_split_branches_unchanged() -> None:
    conditional = If(
        (),
        (InstructionWithPos(Nop(), 1, 1), InstructionWithPos(Else(), 2, 1)),
        (InstructionWithPos(Nop(), 3, 1), InstructionWithPos(End(), 4, 1)),
    )
    assert _restore_if_branches(conditional) == conditional


def test_unexpected_if_layout_rejected() -> None:
    conditional = If((), (InstructionWithPos(Else(), 1, 1), Nop(), End()), (End(),))
    with pytest.raises(ParseError, match='Unexpected if/else instruction layout'):
        _restore_if_branches(conditional)


def test_data_count_preserves_module() -> None:
    original = HEADER + TYPES + FUNCTIONS + MEMORY + CUSTOM + CODE + DATA
    with_count = HEADER + TYPES + FUNCTIONS + MEMORY + DATA_COUNT + CUSTOM + CODE + DATA
    assert wasm2kast(with_count) == legacy_wasm2kast(BytesIO(original))
    assert wasm2kast(original) == legacy_wasm2kast(BytesIO(original))


def test_empty_data_count() -> None:
    assert wasm2kast(HEADER + bytes.fromhex('0c 01 00')) == legacy_wasm2kast(BytesIO(HEADER))


def test_padded_data_count() -> None:
    original = HEADER + MEMORY + DATA
    with_count = HEADER + MEMORY + bytes.fromhex('0c 05 81 80 80 80 00') + DATA
    assert wasm2kast(with_count) == legacy_wasm2kast(BytesIO(original))


@pytest.mark.parametrize(
    'wasm_bytes',
    [
        HEADER + DATA_COUNT + DATA_COUNT,
        HEADER + bytes.fromhex('0c 01 00 0c 01 00'),
        HEADER + DATA_COUNT,
        HEADER + MEMORY + bytes.fromhex('0c 01 00') + DATA,
        HEADER + MEMORY + bytes.fromhex('0c 01 02') + DATA,
        HEADER + TYPES + FUNCTIONS + MEMORY + CODE + DATA_COUNT + DATA,
        HEADER + MEMORY + DATA + DATA_COUNT,
        HEADER + DATA_COUNT + MEMORY + DATA,
        HEADER + bytes.fromhex('0c 00'),
        HEADER + bytes.fromhex('0c 02 00 00'),
        HEADER + bytes.fromhex('0c 01 80'),
        HEADER + bytes.fromhex('0c 02 00'),
        HEADER + bytes.fromhex('0c 05 ff ff ff ff 10'),
        HEADER + bytes.fromhex('0c 06 80 80 80 80 80 00'),
        HEADER + bytes.fromhex('0d 00'),
    ],
)
def test_invalid_data_count_or_unknown_section(wasm_bytes: bytes) -> None:
    with pytest.raises((ParseError, MalformedModule)):
        wasm2kast(wasm_bytes)


@pytest.mark.parametrize('opcode', ['fc 08 00 00', 'fc 09 00', 'fc 0a 00 00', 'fc 0b 00'])
def test_bulk_memory_instructions_remain_unsupported(opcode: str) -> None:
    args = b'' if opcode == 'fc 09 00' else bytes.fromhex('41 00 41 00 41 00')
    body = b'\x00' + args + bytes.fromhex(opcode) + b'\x0b'
    code = bytes([10, len(body) + 2, 1, len(body)]) + body
    with pytest.raises(ParseError, match='Unknown opcode'):
        wasm2kast(HEADER + TYPES + FUNCTIONS + MEMORY + DATA_COUNT + code + DATA)


def test_passive_data_not_reinterpreted_as_active() -> None:
    # This valid passive segment also parses under the old active-segment
    # encoding: its length 65 looks like i32.const, followed by offset 0/end.
    data = b'\x01\x01\x41\x00\x0b\x3e' + b'a' * 62
    section = bytes([11, len(data)]) + data
    with pytest.raises(ParseError, match='Unsupported data segment mode'):
        wasm2kast(HEADER + MEMORY + DATA_COUNT + section)


def test_explicit_memory_data_remains_unsupported() -> None:
    section = bytes.fromhex('0b 0a 01 02 00 41 00 0b 03 61 62 63')
    with pytest.raises(ParseError, match='Unsupported data segment mode'):
        wasm2kast(HEADER + MEMORY + DATA_COUNT + section)
