"""ROM transport and executable serial stage addresses, without inference."""
import os
from pathlib import Path
import sys

os.environ.setdefault('QWEN_O4_TP', '4')
os.environ.setdefault('HDC_SU_WIDTH', '64')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import numpy as np
import pytest
import torch
import qwen_rom_dspark_images as M


def row(name, n, k):
    r = M.matrix(0, name, n, k)
    r.update(scale_base=0, code_span_words=r['words'],
             scale_span_words=r['rounds'] * (M.GROUPS // r['split']) * M.I.INTERLEAVE)
    return r


def test_matrix_transport_raw_partials_and_scale_padding(tmp_path):
    r = row('o', 16, 256)
    codes = np.arange(16*256, dtype=np.int32).reshape(16, 256).astype(np.int8)
    scales = np.arange(16, dtype=np.uint16) + 0x3f80
    depth = M.write_matrix_images(tmp_path, {'o': (codes, scales)}, [r])
    code_lines = (tmp_path/'matrix_int8.hex').read_text().splitlines()
    scale_lines = (tmp_path/'matrix_scale_bf16.hex').read_text().splitlines()
    assert len(code_lines) == r['words']
    assert len(scale_lines) == depth
    # Decode actual little-lane vector order: split group, lane, K index.
    transport = np.frombuffer(bytes.fromhex(code_lines[0])[::-1], dtype=np.int8)
    assert np.array_equal(transport[:16], codes[:16, 0])
    assert np.array_equal(transport[16:32], codes[:16, 1])
    assert scale_lines[0] == '3f80' * M.I.W_LANES  # raw O partials, not real row scale
    assert scale_lines[-1] == '3f80' * M.I.W_LANES


def test_projection_payload_and_physical_field_fit():
    fc = row('fc', 1024, 20480)
    w2 = row('markov_w2', 37984, 256)
    dims = [('qkv', 1536, 4096), ('o', 4096, 1024),
            ('gu', 6144, 4096), ('down', 4096, 3072)]
    assert 20016 + fc['words'] + 5*sum(row(*d)['words'] for d in dims) + w2['words'] == 22920
    assert 22920 < 6*4096
    lay = M.FP.LayerZero(None, 2, [fc]*4)
    with pytest.raises(ValueError):
        M.projection_program(lay, fc, 0, 32768)
    for r in (fc, w2):
        program = M.projection_program(lay, r, 0, 32768, enabled=True)
        me = [f for f in program if f['unit'] == M.I.UNIT_ME]
        assert sum(f['me_nout'] for f in me) == r['rows']
        assert all(f['me_xbase'] == 0 and f['me_oen'] == 1 and f['me_amax'] == 0 for f in me)
        assert me[0]['me_obase'] == 32768//M.I.W_LANES
        assert all(f['barrier'] and not f['chase'] for f in program)
        words, desc = M.encode_program(program)
        assert words and len(desc) == 1
        assert program[-1]['_coll'][0] == M.P.COLL_END


def test_context_ingest_bypasses_input_norm_and_writes_real_slot():
    rows = [row(*d) for d in [('qkv', 1536, 4096), ('o', 4096, 1024),
                               ('gu', 6144, 4096), ('down', 4096, 3072)]]
    lay = M.FP.LayerZero(None, 1, rows)
    lay.norm_fold = False
    program = M.context_kv_program(lay, 15, enabled=True)
    assert program[0]['unit'] == M.I.UNIT_ME
    assert sum(f['unit'] == M.I.UNIT_ME for f in program) == 1
    vm, _ = M.FP.vm_map()
    assert program[0]['me_xbase'] == vm['H']
    writes = [f for f in program if f.get('dst') == M.I.DST_KV]
    assert len(writes) == 3  # V plus two K RoPE halves
    assert writes[0]['d_base'] == lay.v_elem(0, 0, 15, 0)
    assert writes[1]['d_base'] == lay.k_elem(0, 0, 15, 0)
    assert writes[2]['d_base'] == lay.k_elem(0, 0, 15, lay.half)
    assert all(f['barrier'] and not f['chase'] for f in program)
    assert not any(f.get('c_base') == lay.cb[0, 'in'] and f.get('c_src') == M.I.SRC_ALT
                   for f in program)
    assert len(M.encode_program(program)[1]) == 1


def test_real_norms_and_post_fold_scales(monkeypatch):
    rows = [row(*d) for d in [('qkv', 1536, 4096), ('o', 4096, 1024),
                               ('gu', 6144, 4096), ('down', 4096, 3072)]]
    lay = M.FP.LayerZero(None, 0, rows)
    norms = {'in': np.full(4096, 1.5, dtype=np.float32),
             'post': np.full(4096, 2.5, dtype=np.float32),
             'qn': np.full(128, 3.5, dtype=np.float32),
             'kn': np.full(128, 4.5, dtype=np.float32)}
    matrices = {n: (None, np.full(4096, 0x4000+i, dtype=np.uint16))
                for i, n in enumerate(('o', 'down'))}
    monkeypatch.setattr(M.FP, 'TMAX', 2)
    data, bases = M.constants(norms, matrices, lay)
    assert np.all(data[lay.cb[0, 'in']:4096, 0] == 1.5)
    assert np.all(data[lay.cb[0, 'post']:lay.cb[0, 'post']+4096, 0] == 2.5)
    assert np.all(data[lay.cb[0, 'qk']:lay.cb[0, 'qk']+lay.NH*128, 0] == 3.5)
    for i, base in enumerate(bases):
        assert np.all(data[base:base+4096, 0].view(np.uint32) == (0x4000+i)<<16)


def test_invalid_configuration_creates_no_output(tmp_path):
    out = tmp_path/'output'
    with pytest.raises(ValueError):
        M.emit(tmp_path, out, -1, 3, enabled=True)
    assert not out.exists()
    with pytest.raises(ValueError):
        M.split_rows(torch.zeros((5, 4)), torch.zeros((5, 1)), 0, 'rows')
