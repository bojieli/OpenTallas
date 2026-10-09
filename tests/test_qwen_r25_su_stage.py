"""Qwen half-head mapping and negative controls against independent RoPE."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import qwen_r25_su_stage as S
import rtl_hdc_v41x_vec_campaign as C


def test_full_tp4_rope_stage():
    assert S.check_reference() == 0
    assert len(S.program()) == 20
    assert sum(f['nin'] * f['nout'] for f in S.program()) == 1280
    for f in S.program():
        C.encode(f)


def test_adjacent_pair_mutant_rejected():
    assert S.check_reference('adjacent_pair') > 0


def test_sine_sign_mutant_rejected():
    assert S.check_reference('missing_sign') > 0
