"""S81-CORE-LAT-R16: calibrated family-menu re-plan (core_family_slice.replan_structure) -- structure + selection rule."""
import core_family_slice as S


def test_menu_splits_cover_family_menu():
    sp = S._menu_splits({"menu": [1, 2, 4, 8]})
    assert [2, 2, 1] in sp and [2, 2, 2, 8] in sp and [2, 2, 8, 8] in sp
    assert all(x[:2] == [2, 2] for x in sp) and len(sp) == len({tuple(x) for x in sp}) == 10


def test_splits_override_only_when_given():
    assert S.splits_for(3655, {"leaf_target": 48}) == [2, 2, 4, 4]
    assert S.splits_for(3655, {"leaf_target": 48, "splits_override": [2, 2, 2, 8]}) == [2, 2, 2, 8]


def test_replan_picks_min_predicted_error_among_gate_passing(monkeypatch):
    plans = {("std", (2, 2, 4, 4)): (265.8, 208.7, 19.0), ("ndr2w", (2, 2, 2, 8)): (231.3, 178.0, 9.5),
             ("ndr2w", (2, 2, 2, 4)): (222.0, 175.0, 31.0)}       # best latency but fails the 20 ps window gate

    def fake_plan(geo, fam, libtt, libff, name, trunk_cal=None):
        key = (fam["wire"], tuple(fam["splits_override"]))
        if key not in plans:
            raise ValueError("shared wire at T0")
        tt, ff, w = plans[key]
        lat = lambda m: dict(mean=m, window=w, leaf_out_slew_max=40.0)
        return dict(TT=lat(tt), FF=lat(ff), n_cells=100, stages=[8], leaf_spread_max=dict(n_gt_40=0))

    monkeypatch.setattr(S, "plan", fake_plan)
    cal = dict(built_TT=294.0, built_FF=224.8, plan_TT=265.83, plan_FF=208.71)
    rec, fam = S.replan_structure("geo", {"menu": [1, 2, 4, 8], "wire": "std"}, "tt", "ff", "x", cal, jobs=1)
    ch = rec["calibrated_replan"]["chosen"]
    assert (ch["wire"], ch["splits"]) == ("ndr2w", [2, 2, 2, 8]) and fam["wire"] == "ndr2w"
    assert ch["predicted_built"] == {"TT": 259.47, "FF": 194.09} and ch["band"] == {"TT": "IN", "FF": "IN"}
    assert any(c.get("error") for c in rec["calibrated_replan"]["candidates"])
