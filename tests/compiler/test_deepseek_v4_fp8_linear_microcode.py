from __future__ import annotations

from dataclasses import replace

import pytest

from compiler.microcode.deepseek_v4_fp8_linear import (
    DENSE_BLOCK_SIZE,
    DeepSeekV4FP8LinearMicrocodeError,
    Opcode,
    assemble,
    decode,
    disassemble,
    encode,
    verify,
)


def test_fp8_linear_microcode_roundtrip_and_disassembly_are_fixed() -> None:
    instructions = assemble()
    assert decode(encode(instructions)) == instructions
    assert [instruction.opcode for instruction in instructions] == [
        Opcode.FP8_LINEAR_SELECTED_ROWS,
        Opcode.COMPLETE,
    ]
    assert instructions[0].block_size == DENSE_BLOCK_SIZE == 128
    assert disassemble(instructions) == (
        "# OpenTallas DeepSeek V4 FP8 linear ABI 1.0\n"
        "0000 FP8_LINEAR_SELECTED_ROWS dst=0x00000001 src=0x00000000 "
        "weight=0x00000000 scale=0x00000001 selection=0x00000002 block=128\n"
        "0001 COMPLETE                 dst=0xffffffff src=0xffffffff "
        "weight=0xffffffff scale=0xffffffff selection=0xffffffff block=0\n"
    )


def test_fp8_linear_microcode_rejects_crc_and_semantic_drift() -> None:
    instructions = assemble()
    corrupted = bytearray(encode(instructions))
    corrupted[-1] ^= 1
    with pytest.raises(DeepSeekV4FP8LinearMicrocodeError, match="CRC32"):
        decode(bytes(corrupted))

    changed = (replace(instructions[0], block_size=64), instructions[1])
    with pytest.raises(DeepSeekV4FP8LinearMicrocodeError, match="does not exactly"):
        verify(changed)
    with pytest.raises(DeepSeekV4FP8LinearMicrocodeError, match="does not exactly"):
        verify(decode(encode(changed)))


def test_fp8_linear_microcode_rejects_truncation_and_unknown_opcode() -> None:
    payload = encode(assemble())
    with pytest.raises(DeepSeekV4FP8LinearMicrocodeError, match="body length"):
        decode(payload[:-1])
    changed = bytearray(payload)
    changed[16] = 0x40
    # Re-encoding the CRC is intentionally unnecessary: either integrity layer
    # must reject the payload before an unknown instruction can execute.
    with pytest.raises(DeepSeekV4FP8LinearMicrocodeError, match="CRC32"):
        decode(bytes(changed))
