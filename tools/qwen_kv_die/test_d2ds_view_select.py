"""KVR-VIEWS 10-19: d2ds_view_select binds only a CLOSED view hardened at the die's TXDP / NTX (fail closed otherwise)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d2ds_view_select as S  # noqa: E402

TX, NTX = 0x03030418, 3


def kit(root, txdp, ntx=NTX, view=True):
    kd = root / 'physical/ref_tile/qkd_d2d_static_r7v'
    vd = kd / 'views/qkd_d2d_static'
    vd.mkdir(parents=True)
    (kd / 'spec.json').write_text(json.dumps(dict(top='qkd_d2d_static', params=dict(NTX=ntx, TXDP=txdp))))
    if view:
        for f in ('qkd_d2d_static.lef', 'qkd_d2d_static_tt.lib', 'qkd_d2d_static_ff.lib', 'insertion.json'):
            (vd / f).write_text('x')


def test_absent_view_keeps_frame(tmp_path):
    kit(tmp_path, TX, view=False)
    assert S.select('auto', root=tmp_path, die_txdp=TX, die_ntx=NTX)[0] == 0
    assert S.select('auto', root=tmp_path, die_txdp=TX, die_ntx=NTX)[1]['bind'] is None
    assert S.select('1', root=tmp_path, die_txdp=TX, die_ntx=NTX)[0] == 2


def test_matching_view_binds(tmp_path):
    kit(tmp_path, TX)
    rc, rec = S.select('auto', root=tmp_path, die_txdp=TX, die_ntx=NTX)
    assert rc == 0 and rec['bind'] == 'physical/ref_tile/qkd_d2d_static_r7v/views/qkd_d2d_static'


def test_mismatched_view_fails_closed(tmp_path):
    kit(tmp_path, 0x03030417)
    rc, rec = S.select('auto', root=tmp_path, die_txdp=TX, die_ntx=NTX)
    assert rc == 3 and rec['bind'] is None and rec['decision'] == 'FAIL'
    assert S.select('auto', root=tmp_path, die_txdp=TX, die_ntx=2)[0] == 3


def test_off(tmp_path):
    kit(tmp_path, TX)
    assert S.select('0', root=tmp_path)[1]['bind'] is None


def sfm_kit(root, txdp, ntx=NTX, top='qkd_d2d_static_sfm'):
    kd = root / 'physical/ref_tile/qkd_d2d_static_r7w_sfm2'
    vd = kd / 'views' / top
    vd.mkdir(parents=True)
    (kd / 'spec.json').write_text(json.dumps(dict(top=top, params=dict(NTX=ntx, TXDP=txdp, SAFE_RC=1, SRAMV=2, FEG=1))))
    for f in (f'{top}.lef', f'{top}_tt.lib', f'{top}_ff.lib', 'insertion.json'):
        (vd / f).write_text('x')


def test_sfm_view_binds_under_its_top(tmp_path):
    # KV-BIND4: the r7w_sfm2 view lives under views/qkd_d2d_static_sfm (spec.json top), not views/qkd_d2d_static
    sfm_kit(tmp_path, TX)
    rc, rec = S.select('1', kit='qkd_d2d_static_r7w_sfm2', root=tmp_path, die_txdp=TX, die_ntx=NTX)
    assert rc == 0 and rec['decision'] == 'BIND' and rec['top'] == 'qkd_d2d_static_sfm'
    assert rec['bind'] == 'physical/ref_tile/qkd_d2d_static_r7w_sfm2/views/qkd_d2d_static_sfm'
    assert rec['view_params']['SRAMV'] == 2
    assert S.select('auto', kit='qkd_d2d_static_r7w_sfm2', root=tmp_path, die_txdp=TX + 1, die_ntx=NTX)[0] == 3


def test_unknown_top_fails_closed(tmp_path):
    sfm_kit(tmp_path, TX, top='qkd_d2d_static_ovl_sfm')
    rc, rec = S.select('auto', kit='qkd_d2d_static_r7w_sfm2', root=tmp_path, die_txdp=TX, die_ntx=NTX)
    assert rc == 3 and rec['bind'] is None
