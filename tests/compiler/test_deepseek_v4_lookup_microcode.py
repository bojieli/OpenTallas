from __future__ import annotations

import pytest

from compiler.microcode.deepseek_v4_lookup import (
    HEADER,
    RECORD,
    DeepSeekV4LookupMicrocodeError,
    Instruction,
    Opcode,
    assemble,
    decode,
    disassemble,
    encode,
    verify,
)


def test_lookup_microcode_round_trips_and_disassembles() -> None:
    instructions = assemble(4)
    payload = encode(instructions)
    assert len(payload) == HEADER.size + 4 * RECORD.size
    assert decode(payload) == instructions
    verify(decode(payload), 4)
    assert disassemble(instructions) == (
        "# OpenTallas DeepSeek V4 lookup ABI 1.0\n"
        "0000 TOKEN_EMBED dst=0x00000001 src=0x00000000 "
        "resource=0x00000000 imm=0\n"
        "0001 HC_EXPAND   dst=0x00000002 src=0x00000001 "
        "resource=0xffffffff imm=4\n"
        "0002 HASH_ROUTE  dst=0x00000003 src=0x00000000 "
        "resource=0x00000001 imm=0\n"
        "0003 COMPLETE    dst=0xffffffff src=0xffffffff "
        "resource=0xffffffff imm=0\n"
    )


def test_lookup_microcode_rejects_corruption_and_semantic_drift() -> None:
    instructions = assemble(4)
    payload = bytearray(encode(instructions))
    payload[-1] ^= 1
    with pytest.raises(DeepSeekV4LookupMicrocodeError, match="CRC32"):
        decode(bytes(payload))

    changed = list(instructions)
    changed[1] = Instruction(Opcode.HC_EXPAND, 2, 1, 0xFFFFFFFF, 3)
    with pytest.raises(DeepSeekV4LookupMicrocodeError, match="exactly lower"):
        verify(tuple(changed), 4)


@pytest.mark.parametrize("value", [0, -1, True, 1 << 32])
def test_lookup_microcode_rejects_invalid_hc_multiplier(value: object) -> None:
    with pytest.raises(DeepSeekV4LookupMicrocodeError, match="hc_multiplier"):
        assemble(value)  # type: ignore[arg-type]
