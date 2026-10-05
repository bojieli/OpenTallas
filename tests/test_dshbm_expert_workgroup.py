import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import numpy as np
import pytest
from dshbm_expert_workgroup import steer, weight_lines, restore_rows


def test_source_ids_and_all_row_partitions():
    ids = (3, 8, 49, 117, 259, 266)
    all_rows = {}
    for die in range(96):
        ds = steer(ids, die)
        assert [d.sm for d in ds] == list(range(24))
        for d in ds:
            all_rows.setdefault((d.expert, d.matrix), []).extend(range(d.row_start, d.row_stop))
    assert len(all_rows) == 12
    assert all(rows == list(range(2304)) for rows in all_rows.values())


@pytest.mark.parametrize('ids', [(0,0,1,2,3,4), (5,4,3,2,1,0), (0,1,2,3,4,384), (False,1,2,3,4,5)])
def test_cannot_substitute_or_alias_router_ids(ids):
    with pytest.raises(ValueError): steer(ids, 0)


def test_every_native_line_recovers_original_bytes_and_tail_padding():
    from rtl_gpu_sm_exact import issue_order
    p = np.arange(12*2560, dtype=np.uint32).astype(np.uint8).reshape(12,2560)
    e = np.arange(12*160, dtype=np.uint32).astype(np.uint8).reshape(12,160)
    lines = weight_lines(p,e)
    assert len(lines) == 288
    for word, (r,g,t) in zip(lines,issue_order(12,3,8,True)):
        for lane in range(8):
            b = (g*8+lane)*8+t
            got = (word>>(128*lane))&((1<<128)-1)
            scale = (word>>(1024+8*lane))&255
            if b<160:
                assert got == int.from_bytes(p[r,b*16:(b+1)*16].tobytes(),'little')
                assert scale == int(e[r,b])
            else: assert got == scale == 0


def test_results_restore_source_identity_and_order():
    ds = steer((0,2,4,6,8,383),95)
    results = {d.sm: list(range(d.row_start,d.row_stop)) for d in reversed(ds)}
    out = restore_rows(ds,results)
    assert len(out)==12
    assert all(rows==[(i,i) for i in range(2280,2304)] for rows in out.values())
    del results[23]
    with pytest.raises(ValueError): restore_rows(ds,results)


def test_real_source_packing_reuses_native_generator_without_rng():
    from dshbm_expert_workgroup import sm_vectors
    p = np.full((12,2560),0x21,dtype=np.uint8)
    scales = np.full((12,160),121,dtype=np.uint8)
    x = np.zeros(5120,dtype=np.float32)
    x[0],x[4095],x[-1] = 1.0,-2.0,0.5
    g = sm_vectors(p,scales,x)
    assert tuple(g['lines'])==weight_lines(p,scales)
    assert len(g['gold'][0])==12 and len(g['xw'])==24
    assert g['fmt']==2 and g['Gn']==3 and g['R']==12
