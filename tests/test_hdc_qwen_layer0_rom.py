"""INT8 engine packing and the post-TP scale ISA schedule."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa as I  # noqa: E402
import hdc_qwen_fullshape_program as F  # noqa: E402
import hdc_qwen_layer0_rom as R  # noqa: E402


def test_code_and_scale_word_address_round_trip():
    n, k, groups, split = 130, 16, 64, 1
    codes = np.arange(n * k, dtype=np.uint8).reshape(n, k).view(np.int8)
    scales = np.arange(n, dtype=np.uint16) + 0x3F00
    words = list(R.engine_word_arrays(codes, scales, split=split, groups=groups))
    assert len(words) == 64 * I.INTERLEAVE
    for row in (0, 15, 16, 127, 128, 129):
        tile, slot, lane = row // 128, (row // 16) % 8, row % 16
        for col in (0, 7, 15):
            word = col * 8 + slot
            group = tile
            assert words[word][0][group * 16 + lane] == codes[row, col].view(np.uint8)
        scale_addr = tile * 8 + slot
        assert words[scale_addr][1][lane] == scales[row]
    assert all(np.all(words[i][0] == 0) for i in range(128, len(words)))
    assert words[8][1][2] == 0x3F80  # padded row 130
    assert np.all(words[-1][1] == 0x3F80)


def test_raw_partial_scale_and_post_fold_program():
    codes = np.array([[1, -2] * 8], dtype=np.int8)
    scales = np.array([0x3E00], dtype=np.uint16)
    code, scale = next(R.engine_word_arrays(codes, scales, split=1, groups=4,
                                            raw_partial=True))
    assert int(code[0]) == 1
    assert int(scale[0]) == 0x3F80
    report = F.profile(0, post_scale_bases=(600000, 604096))
    program = [I.decode(int(word, 16)) for word in report['program_hex']]
    post = [f for f in program if f['unit'] == I.UNIT_SU and f['c_base'] in (600000, 604096)]
    assert len(post) == 2
    assert [f['c_base'] for f in post] == [600000, 604096]
    assert all(f['mc'] == I.MC_C and f['dst'] == I.DST_VM and f['su_nin'] == 4096 for f in post)
    assert report['allreduce_segments'] == 4


def test_independent_compact_code_and_scale_bases():
    matrices = {
        name: (np.zeros((n, 16), dtype=np.int8), np.full(n, 0x3F80, dtype=np.uint16))
        for name, n in (('qkv', 128), ('o', 16), ('gu', 256), ('down', 32))
    }
    shared = R.matrix_plan(matrices)
    compact = R.matrix_plan(matrices, compact_banks=True)
    assert compact[-1]['end'] == sum(row['code_span_words'] for row in compact)
    assert compact[-1]['scale_end'] == sum(row['scale_span_words'] for row in compact)
    assert compact[-1]['end'] < shared[-1]['end']
    for previous, current in zip(compact, compact[1:]):
        assert current['base'] == previous['end']
        assert current['scale_base'] == previous['scale_end']
    assert any(row['base'] != row['scale_base'] for row in compact)
