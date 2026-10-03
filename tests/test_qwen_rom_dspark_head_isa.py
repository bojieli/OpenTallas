"""Check all base-logit rows remain live for the exact Markov stream add."""
import os
from pathlib import Path
import sys

os.environ.setdefault('QWEN_O4_TP', '4')
os.environ.setdefault('HDC_SU_WIDTH', '64')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import pytest
import qwen_rom_dspark_images as M
import qwen_rom_dspark_head_isa as H


@pytest.mark.parametrize('slots', [3, 7])
def test_base_rows_cover_vocabulary_once_without_early_argmax(slots):
    dims = [('qkv', 1536, 4096), ('o', 4096, 1024),
            ('gu', 6144, 4096), ('down', 4096, 3072)]
    rows = [M.matrix(0, *d) for d in dims]
    lay = M.FP.LayerZero(None, 3, rows)
    head = M.matrix(18432, 'lm_head', 37984, 4096)
    head['scale_base'] = 20480
    with pytest.raises(ValueError):
        H.base_logits_program(lay, head, 123456, slots, 49)
    program, layout = H.base_logits_program(lay, head, 123456, slots, 49, enabled=True)
    written = set()
    for f in program:
        assert f['barrier'] and not f['chase']
        if f['unit'] == M.I.UNIT_ME:
            assert not f['me_amax'] and not f['me_amc'] and f['me_oen']
            addresses = set(M.P.me_write_slots(f, M.GROUPS))
            assert not addresses & written
            written |= addresses
    expected = {base+i for base in layout['base_logits_vm'] for i in range(37984)}
    assert written == expected
    assert layout['markov_bias_vm'] > max(written)
    assert layout['vm_elements'] <= 1 << 20
    assert layout['vocabulary_row0'] == 113952
    norms = [f for f in program if f.get('c_src') == M.I.SRC_ALT and f.get('c_base') == 123456]
    assert len(norms) == slots
    words, desc, _ = H.encode_base_logits(lay, head, 123456, slots, 49, enabled=True)
    assert words and len(desc) == 1
    assert program[-1]['_coll'][0] == M.P.COLL_END
