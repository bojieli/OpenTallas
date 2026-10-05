"""Checks of tools/qwen_rom_speculation_recheck.py (Qwen ROM speculation re-check, 2026-10-03)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_rom_speculation_recheck as S  # noqa: E402

REC = ROOT / "results/speculative/qwen_rom_speculation_recheck_20261003/pricing.json"


def test_basis_reproduces_measured_and_selected_terms():
    assert S.BODY == 2595
    assert S.layer(1) == 2595 + 2 * 624 + 1700 == 5543
    assert S.ar_token() == 36 * 5543 + 3042 == 202590


def test_me_issue_equals_program_descriptors():
    code = ("import hdc_qwen_fullshape_program_w12 as F, hdc_program as P, hdc_isa as I\n"
            "from hdc_qwen_fullshape_placement_w12 import placement\n"
            "vm,_=F.vm_map(); lay=F.LayerZero(placement(),0)\n"
            "with F.program_geometry(vm): prog=P.build_program(lay,layers=[0],embed=False,head=False,scale_bases=True)\n"
            "print(sum(f['me_tiles']*f['me_k']*I.INTERLEAVE for f in prog if f['unit']==I.UNIT_ME and not f.get('me_wsrc')))\n")
    env = dict(os.environ, QWEN_O4_TP="4", QWEN_O4_GROUPS="6144")
    out = subprocess.check_output([sys.executable, "-c", code], cwd=ROOT / "tools", env=env, text=True)
    assert int(out.split()[-1]) == sum(S.ME_ISSUE.values()) == 512


def test_increments_and_monotonicity():
    assert S.layer(2) - S.layer(1) == 512 + 4 + 473 + 512 + 1400 + 40 + 72
    assert S.layer(2, m_attn=2) - S.layer(1) == 512 + 4 + 473 + 512 + 40 + 72
    assert S.layer(2, ar="existing") - S.layer(1) == 512 + 4 + 473 + 1248 + 1512
    for p in range(1, 16):
        assert S.layer(p + 1) > S.layer(p)
        assert S.layer(p, m=2) <= S.layer(p)
        assert S.layer(p, su="overlap") <= S.layer(p)


def test_tau_bounds_and_dspark_cap():
    T = S.taus()
    for B, v in T.items():
        for c in v:
            assert 1.0 <= S.tau_for("dflash", c, B, T) <= B
            assert S.tau_for("dflash", c, B, T) <= S.tau_for("dspark", c, B, T) <= B


def test_record_reproduces():
    rec = json.loads(REC.read_text())
    _, ar, res = S.price()
    assert rec["basis"]["token_ar_cycles"] == ar
    assert rec["results"] == json.loads(json.dumps(res))
