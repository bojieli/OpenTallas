"""FABLE-FIX-QC-N 11-17 (QC event N2): qc_fabric_transport holds the HI_PAD of a plan hard core.

N START added one cycle on the S head column 2 (lane hc2->cws2).  The hook balanced the S columns with pads [1,1,0,1], the S
roots moved by +1 and HI_PAD (S far - N far) rose by 1 on every station: 44 HARD_CORE_PARAM_WRAP errors on 11 st_a types whose
masters are built with the old pad.  With the hold, the four N head columns take one uniform pad and HI_PAD stays."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_fabric_transport as QFT  # noqa: E402


class View:
    """Smallest bound view derive() accepts: every shift 0 except the given (leaf, port) entries."""

    def __init__(self, shifts=None, targets=None):
        self.shifts = shifts or {}
        self.targets = targets

    def delta(self, path, port, bits=None):
        return self.shifts.get((path, port), 0)

    def source(self, path, port):
        cl, _fab, x = path.split(".")
        s, k = cl.split("_")[1], int(cl.split("_")[2])
        c = x.split("_")[2]
        if k == QFT.NEAR["S"]:
            return f"dvs_{s}.u_core.u_sub.u_xh{c}.s_d"
        if k == QFT.NEAR["N"]:
            return f"dvs_{s}.u_core.u_sub.u_xh{c}.n_d"
        near = QFT.NEAR["S"] if k == QFT.FAR["S"] else QFT.NEAR["N"]
        return f"c16_{s}_{near}.u_fab.u_x_{c}_3.b_q"

    def has_port(self, path, port):
        return False

    def hi_pad_targets(self):
        return dict(self.targets or {})


def n_start():
    """+1 on the S near column 2 entry of every slice (the N START lane change)."""
    return {(f"c16_{s}_{QFT.NEAR['S']}.u_fab.u_x_2_0", "b_d"): 1 for s in QFT.SLICES}


def stations(value, regions=range(4)):
    return {f"dvs_{s}.u_core.u_sub.u_r{r}": value for s in QFT.SLICES for r in regions}


def test_without_targets_hi_pad_follows_the_s_side():
    params, rec = QFT.derive(View(n_start()))
    sl = rec["slices"]["W5"]
    assert list(sl["column_pads"]["S"]) == [1, 1, 0, 1] and list(sl["column_pads"]["N"]) == [0, 0, 0, 0]
    assert {r["HI_PAD"] for r in sl["regions"].values()} == {1}
    assert "hi_pad_hold" not in sl


def test_hold_pads_the_n_columns_and_keeps_the_master_pad():
    params, rec = QFT.derive(View(n_start(), stations(0)))
    for s in QFT.SLICES:
        sl = rec["slices"][s]
        assert list(sl["column_pads"]["N"]) == [1, 1, 1, 1] and list(sl["column_pads"]["S"]) == [1, 1, 0, 1]
        assert sl["hi_pad_hold"] == dict(side="N", uniform_pad=1)
        assert {r["HI_PAD"] for r in sl["regions"].values()} == {0}          # the st_b regions follow the same heads
        assert {r["SKEW_N"] for r in sl["regions"].values()} == {QFT.SKEW0}  # a uniform pad does not change the skew lines
        for c in range(4):
            assert params[f"dvs_{s}.u_core.u_sub.u_xh{c}"]["N_PAD"] == 1


def test_matching_plan_is_unchanged():
    base = QFT.derive(View(n_start()))
    held = QFT.derive(View(n_start(), stations(1)))
    assert held[0] == base[0]
    assert held[1]["slices"]["E0"]["hi_pad_hold"] == dict(side=None, uniform_pad=0)


def test_pad_goes_to_the_s_side_when_the_master_pad_is_larger():
    _params, rec = QFT.derive(View(n_start(), stations(3)))
    sl = rec["slices"]["W0"]
    assert list(sl["column_pads"]["S"]) == [3, 3, 2, 3] and sl["hi_pad_hold"] == dict(side="S", uniform_pad=2)
    assert {r["HI_PAD"] for r in sl["regions"].values()} == {3}


def test_two_pads_in_one_slice_are_refused():
    t = stations(0)
    t["dvs_W5.u_core.u_sub.u_r1"] = 1
    with pytest.raises(ValueError, match="one value required"):
        QFT.derive(View(n_start(), t))


def test_pad_above_the_column_limit_is_refused():
    with pytest.raises(ValueError, match="above"):
        QFT.derive(View(n_start(), stations(-QFT.MAX_COLUMN_PAD)))
