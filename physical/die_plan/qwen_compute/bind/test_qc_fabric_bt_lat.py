"""QC-RC97-BT2 11-24 (rc97): qc_fabric_transport binds a plan region core's BT_LAT on all eight regions of its slice.

The registered btab read (OT_BTAB_S4R) adds one edge to the bt_word -> bt_q round trip of a slice; the four st_a region
hard cores carry BT_LAT 2 in their param_wrap, and the four st_b regions of the same slice (same btab, r_d joined on
region 0's r_v) must take the same BT_LAT.  A plan without the row binds byte-identically."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_fabric_transport as QFT  # noqa: E402
from test_qc_fabric_hi_pad_hold import View  # noqa: E402


class BtView(View):
    def __init__(self, bt=None):
        super().__init__()
        self.bt = bt or {}

    def bt_lat_targets(self):
        return dict(self.bt)


def st_a(slice_, value, define=True):
    return {f"dvs_{slice_}.u_core.u_sub.u_r{r}": (value, define) for r in range(4)}


def test_no_rows_binds_unchanged():
    assert QFT.derive(BtView()) == QFT.derive(View())
    assert QFT.derive(BtView({**st_a("E3", 1, False)}))[0] == QFT.derive(View())[0]


def test_bt2_slice_sets_all_eight_regions_only_there():
    params, rec = QFT.derive(BtView({**st_a("E3", 2), **st_a("W5", 2)}))
    base, _ = QFT.derive(View())
    for s in ("E3", "W5"):
        assert rec["slices"][s]["bt_lat"] == 2
        for r in range(8):
            u = f"dvs_{s}.u_core.u_sub.u_r{r}"
            assert params[u]["BT_LAT"] == 2
            assert {k: v for k, v in params[u].items() if k != "BT_LAT"} == base[u]
    for s in set(QFT.SLICES) - {"E3", "W5"}:
        assert "bt_lat" not in rec["slices"][s]
        assert all("BT_LAT" not in params[f"dvs_{s}.u_core.u_sub.u_r{r}"] for r in range(8))


def test_bt2_without_the_registered_btab_is_refused():
    with pytest.raises(ValueError, match="OT_BTAB_S4R"):
        QFT.derive(BtView(st_a("E1", 2, define=False)))


def test_mixed_bt_lat_in_one_slice_is_refused():
    t = st_a("E5", 2)
    t["dvs_E5.u_core.u_sub.u_r2"] = (1, True)
    with pytest.raises(ValueError, match="one value per slice"):
        QFT.derive(BtView(t))
