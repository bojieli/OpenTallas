"""18-bit Qwen row offsets reuse reserved bits without changing word widths."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa as I  # noqa: E402
import hdc_qwen_fullshape_isa as Q  # noqa: E402


@pytest.mark.parametrize('row', [0, 65535, 65536, 75968, 151935, 262143])
def test_row_offset_round_trip(row):
    instruction = Q.encode_instruction({'unit': I.UNIT_ME, 'me_row0': row})
    assert instruction.bit_length() <= I.INSTR_BITS
    assert Q.decode_instruction(instruction)['me_row0'] == row
    desc = Q.encode_descriptor(2, 255, 128, 4095, row)
    assert desc.bit_length() <= 64
    assert Q.decode_descriptor(desc) == {'kind': 2, 'vm_word': 255,
                                         'words': 128, 'program_base': 4095, 'row0': row}
    if row < 65536:
        assert instruction == I.encode(unit=I.UNIT_ME, me_row0=row)
        assert desc == 2 | (255 << 2) | (128 << 10) | (4095 << 32) | (row << 48)


def test_out_of_range_rejected():
    with pytest.raises(ValueError, match='18 bits'):
        Q.encode_instruction({'me_row0': 1 << 18})
    with pytest.raises(ValueError, match='exceeds'):
        Q.encode_descriptor(2, 0, 0, 0, 1 << 18)
