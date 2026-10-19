"""KVR-VIEWS 10-19: the die switches to qkd_pv_rs_hd_f only with a committed f2 native PASS receipt matching the view."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rs_hd_select as S  # noqa: E402


def tree(root, receipt=None, tamper=False):
    vd = root / S.F_VIEW
    vd.mkdir(parents=True)
    (vd / 'qkd_pv_rs_hd_f.lef').write_text('lef')
    (vd / 'qkd_pv_rs_hd_f_tt.lib').write_text('lib')
    for f in S.FILES.values():
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_text('sv')
    if receipt:
        shas = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in vd.iterdir()}
        (root / S.F_RECEIPTS / f'native_qkd_pv_rs_hd_f_f2-0473e5d89_{receipt}.json').write_text(
            json.dumps(dict(verdict=receipt, view=S.F_VIEW, view_sha256=shas)))
    if tamper:
        (vd / 'qkd_pv_rs_hd_f.lef').write_text('other')


def test_no_receipt_keeps_r(tmp_path):
    tree(tmp_path)
    assert S.select({}, tmp_path)['rs_hd'] == 'r'
    with pytest.raises(ValueError):
        S.select({'OT_KV_RS_HD': 'f'}, tmp_path)


def test_pass_receipt_switches_auto(tmp_path):
    tree(tmp_path, 'PASS')
    s = S.select({}, tmp_path)
    assert s['rs_hd'] == 'f' and s['rs_d'] == 50 and s['rs_d_delta'] == 1 and s['file'].endswith('qkd_pvw_die_t_f.sv')
    assert S.select({'OT_KV_RS_HD': 'r'}, tmp_path)['rs_hd'] == 'r'


def test_fail_receipt_or_changed_view_keeps_r(tmp_path):
    tree(tmp_path, 'FAIL')
    assert S.select({}, tmp_path)['rs_hd'] == 'r'


def test_view_changed_after_audit(tmp_path):
    tree(tmp_path, 'PASS', tamper=True)
    assert S.select({}, tmp_path)['rs_hd'] == 'r'


def test_branch_today_is_r():
    assert S.select({})['rs_hd'] == 'r'
