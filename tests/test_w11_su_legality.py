"""W11 stream unit: layout legality of the documented configurations (W17 caveat, 2026-10-01).

The unit's results are exact at any N for which every op is layout-legal: a span reduction needs
L = ceil(log2(ceil(n_flat / 2^ls))) <= LV levels, otherwise ot_hdc_v41x_vec faults the op at issue (c_bad).
tools/v41_su_legality.check_op mirrors c_bad on ISA-decoded fields; rtl_hdc_v41x_vec_campaign.layout()['bad']
mirrors it on the bench's fields."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_su_legality as L  # noqa: E402

PROGRAM = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.hex"


def _fullshape_illegal(n, m, lv=7):
    words = [int(x, 16) for x in PROGRAM.read_text().split()]
    return L.check_program(words, n, m, lv)


def test_fullshape_l0_program_is_legal_at_the_spec_width():
    assert _fullshape_illegal(1024, 256) == []          # N1024 / M256: the full-shape configuration
    assert _fullshape_illegal(256, 64) == []


@pytest.mark.parametrize("n,m", [(16, 8), (64, 16)])
def test_narrow_sus_are_not_legal_at_full_shape(n, m):
    bad = _fullshape_illegal(n, m)
    assert bad and all(any("span depth" in r for r in b["reasons"]) for b in bad)


def _bad_at(lay, lv):
    """layout()'s refusal re-graded at LV = lv (layout() folds the campaign bench's LV = 6)."""
    return lay["bad"] and not (lay["span"] and 6 < lay["L"] <= lv)


def test_softmax_fixture_is_legal_at_the_documented_widths():
    import rtl_hdc_v41x_vec_campaign as C
    import w11_su_softmax_spec as W
    for (n, m) in ((16, 8), (1024, 256)):
        for tokens in (128, 640):
            _, _, _, cl = W.cases(n, m, tokens)
            for _, _, ops, _ in cl:
                assert not any(_bad_at(C.layout(f, n, m), 7) for f in ops), (n, m, tokens)


@pytest.mark.skipif(not (Path(os.environ.get("OPENTALLAS_BUILD", ROOT / "build"))
                         / "models/deepseek-v4.1-flash-reduced-v2/model-00001-of-00001.safetensors").exists(),
                    reason="the reduced vehicle's checkpoint is not built here")
def test_reduced_vehicle_is_legal_at_n16_n64_n1024():
    import rtl_hdc_v41x_vec_campaign as C
    recs, *_ = C.vehicle_records()
    ops = [g for g in (C.resolve(f, dyn) for f, dyn, _, _ in recs) if g["nout"] and g["nin"]]
    assert len(ops) > 2000
    for n, m in ((16, 8), (64, 16), (1024, 256)):
        assert not any(C.layout(g, n, m)["bad"] for g in ops), (n, m)
