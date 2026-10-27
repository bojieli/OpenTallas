"""QC-CLK-MESH plan model: H-tree equal by construction, seam classes V1/V2, deck writer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_clk_mesh as Q  # noqa: E402


class _P:
    W, H, name = 4000.0, 3200.0, "toy"


def _build():
    parts = [(0, 0, 2000, 3200, "pa"), (2000, 0, 4000, 3200, "pb")]
    entries = [dict(part="pa", xy_um=[1000.0, 1600.0]), dict(part="pb", xy_um=[3000.0, 1600.0])]
    trunk = dict(len_um=400.0, n_seg=1)
    return parts, Q.build(_P, parts, [], entries, trunk, 8, 8, 2, 2, 216.0, "4w", snap=False)


def test_htree_equal_by_construction():
    _, B = _build()
    L = {round(sum(B["by"][t].get("edge_ideal_um", 0) for t in Q.chain(B["by"], d["tag"], None)), 6) for d in B["drivers"]}
    assert len(L) == 1 and len(B["drivers"]) == 64 and len(B["rroots"]) == 4
    a = {round(d["arr"]["TT"], 6) for d in B["drivers"]}
    assert len(a) == 1


def test_seam_classes_v1_v2():
    parts, B = _build()
    pairs = [("pa", "pb", 3200.0)]
    v1 = Q.pair_classes(B, pairs, {"TT": 5.0, "FF": 4.0})
    v2 = Q.pair_classes(B, pairs, {"TT": 5.0, "FF": 4.0}, continuous=True)
    assert v1[0]["cls"] == "cross_mesh_d0" and v2[0]["cls"] == "seam_joined_mesh"
    assert v2[0]["TT"]["total_ps"] < v1[0]["TT"]["total_ps"]
    assert v2[0]["TT"]["mesh_uncertainty_ps"] == 5.0


def test_deck_writer(tmp_path):
    _, B = _build()
    m = Q.write_deck(B, (0, 1), "TT", tmp_path, "4w", samples=[0, 1],
                     sigma=dict(vt_mV=10.0, wire_rel=0.05, tree_ps_per_stage=2.0, full_path=True))
    d0 = (tmp_path / "s000" / "deck.sp").read_text()
    d1 = (tmp_path / "s001" / "deck.sp").read_text()
    assert "BUFx24v" in d0 and "pre_osdi" in d0 and d0 != d1
    assert m["drivers"] == 16 and m["taps"] == 1
