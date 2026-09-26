from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from pykwasm.wasm2kast import ast2kast
from wasm.exceptions import ParseError  # type: ignore[import-untyped]
from wasm.instructions import Block, Else, End, If, InstructionWithPos, Loop  # type: ignore[import-untyped]
from wasm.parsers import parse_module  # type: ignore[import-untyped]
from wasm.parsers.integers import parse_u32  # type: ignore[import-untyped]
from wasm.parsers.magic import parse_magic  # type: ignore[import-untyped]
from wasm.parsers.version import parse_version  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pyk.kast.inner import KInner
    from wasm.instructions import BaseInstruction  # type: ignore[import-untyped]


def _restore_if_branches(instruction: BaseInstruction) -> BaseInstruction:
    """Repair the pinned parser's failure to recognize position-wrapped Else."""
    if isinstance(instruction, InstructionWithPos):
        return instruction._replace(instruction=_restore_if_branches(instruction.instruction))
    if isinstance(instruction, If):
        then_body = instruction.instructions
        else_body = instruction.else_instructions
        separators = [
            i
            for i, op in enumerate(then_body)
            if isinstance(op, InstructionWithPos) and isinstance(op.instruction, Else)
        ]
        if len(separators) > 1:
            raise ParseError('If instruction contains multiple else clauses')
        if separators and separators[0] != len(then_body) - 1:
            # The buggy parser appends a synthetic Else and leaves only a
            # synthetic End in the else branch, even when a real Else exists.
            if not isinstance(then_body[-1], Else) or len(else_body) != 1 or not isinstance(else_body[0], End):
                raise ParseError('Unexpected if/else instruction layout')
            split = separators[0] + 1
            else_body = then_body[split:-1] + else_body
            then_body = then_body[:split]
        return instruction._replace(
            instructions=tuple(_restore_if_branches(op) for op in then_body),
            else_instructions=tuple(_restore_if_branches(op) for op in else_body),
        )
    if isinstance(instruction, (Block, Loop)):
        return instruction._replace(instructions=tuple(_restore_if_branches(op) for op in instruction.instructions))
    return instruction


def wasm2kast(wasm_bytes: bytes) -> KInner:
    """Read SDK-generated Wasm with optional DataCount metadata.

    The pinned Wasm parser predates DataCount. Validate that section, then pass
    every other section unchanged to the existing parser. Unsupported data
    modes and instructions remain errors; no executable content is rewritten.
    """
    stream = BytesIO(wasm_bytes)
    parse_magic(stream)
    parse_version(stream)
    sections = [wasm_bytes[: stream.tell()]]
    data_count = None
    last_section = 0
    while stream.tell() < len(wasm_bytes):
        section_start = stream.tell()
        section_id = stream.read(1)[0]
        section_size = int(parse_u32(stream))
        payload_start = stream.tell()
        section_end = payload_start + section_size
        if section_end > len(wasm_bytes):
            raise ParseError('Section declared size larger than stream')
        if section_id == 12:
            if data_count is not None:
                raise ParseError('Duplicate DataCount section')
            if last_section >= 10:
                raise ParseError('DataCount section must precede code and data sections')
            payload = BytesIO(wasm_bytes[payload_start:section_end])
            data_count = int(parse_u32(payload))
            if payload.tell() != section_size:
                raise ParseError('DataCount section must contain exactly one u32')
        else:
            if data_count is not None and 1 <= section_id <= 9:
                raise ParseError('DataCount section must follow other standard sections')
            sections.append(wasm_bytes[section_start:section_end])
            if section_id:
                last_section = section_id
        stream.seek(section_end)

    module = parse_module(BytesIO(b''.join(sections)))
    if data_count is not None and data_count != len(module.data):
        raise ParseError(f'DataCount mismatch: declared {data_count}, actual {len(module.data)}')
    # The legacy parser reads the data mode as a memory index. Only mode 0 has
    # the same encoding and meaning; reject passive and explicit-memory modes.
    if any(segment.memory_idx != 0 for segment in module.data):
        raise ParseError('Unsupported data segment mode; only active memory-zero segments are supported')
    module = module._replace(
        funcs=tuple(func._replace(body=tuple(_restore_if_branches(op) for op in func.body)) for func in module.funcs)
    )
    return ast2kast(module)
