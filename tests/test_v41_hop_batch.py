"""tools/rtl_v41_hop_batch_campaign.py: the adopted stage-hop split under the T1 load of other users' collectives."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import rtl_v41_hop_batch_campaign as H  # noqa: E402

REC = ROOT / "results/rtl/v41_hop_batch_campaign.json"
SENS = ROOT / "results/arch/v41_hop_batch_sensitivity.json"


def traffic():
    """A two-stage toy: the hop lands on stage 1 at DAG cycle 1,000 (period 4,000); stage 1 runs one all-reduce
    whose words are produced at 900 and 2,000, and one collective that descends from the hop."""
    ev = {"a": dict(stage=1, cls="all_reduce", words=2, on_path=True, rel=[900, 2000]),
          "b": dict(stage=1, cls="all_reduce", words=1, on_path=True, rel=[1500])}
    return dict(period_cycles=4000.0, events=ev,
                hops=[dict(hop="h", stage=1, ref=1000.0, stage_events=["a", "b"], descendants=["b"])])


def test_background_fill_one_keeps_only_the_users_own_non_descendant_events():
    words, table = H.background(traffic(), 0, 1, -1500, 1500)
    assert sorted(table) == ["u0:a:0"]                     # b descends from the hop: causally after it
    assert [w for w, _ in words] == [-100, 1000]


def test_background_even_spacing_shifts_each_user_by_k_period_over_n():
    words, table = H.background(traffic(), 0, 2, -5000, 5000)
    # user 1 is 2,000 cycles ahead: its words land 2,000 earlier; both of its events count (it is another user)
    got = {k: (v["first_rel"], v["last_rel"]) for k, v in table.items()}
    assert got["u1:a:0"] == (-2100, -1000) and got["u1:b:0"] == (-1500, -1500)
    assert got["u1:a:1"] == (1900, 3000)                  # the next pass, one period later
    assert [w for w, _ in words] == sorted(w for w, _ in words)


def test_background_window_drops_whole_events_outside():
    _, table = H.background(traffic(), 0, 2, -500, 500)
    assert all(v["last_rel"] >= -500 and v["first_rel"] <= 500 for v in table.values())
    assert "u1:b:0" not in table


def test_schemes_cover_full_and_the_adopted_split_under_every_arbiter():
    names = [s for s, _, _ in H.schemes("ar")]
    assert names[:2] == ["bgonly", "full"] and "split20" in names
    assert {"split20_hop_first", "split20_background_first"} <= set(names)


def test_committed_campaign():
    rec = json.loads(REC.read_text())
    s = rec["summary"]
    assert s["all_pass"] and s["bit_exact"] and s["background_in_order"]
    for c in rec["cases"]:
        assert c["background_received"] == c["background_expected"] and c["timeout"] == 0
        if c["hop_words"]:
            assert c["hop_words_received"] == 4 * c["hop_words"]
    # with no load the bench reproduces the lever campaign's hop tails on every stage hop
    lev = s["no_load"]["lever_campaign_ar"]
    assert s["no_load"]["ar"]["full"] == [lev["full"]] and s["no_load"]["ar"]["split20"] == [lev["split20"]]
    # full payload per package puts no word on T1: it never delays another user's collective
    for mode in ("ar", "mtp"):
        for f in s["fills"][mode]["per_fill"].values():
            assert f["schemes"]["full"]["victim_delay_max"] == 0
    # the source pins bind the tree
    import v41_collective_exposure as VX
    assert VX.campaign_binding(rec, REC)["current"]


def test_sensitivity_record_leaves_the_headline():
    rec = json.loads(SENS.read_text())
    lanes = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())["design_point"]
    for ctx, r in rec["headline_batch1"].items():
        assert abs(r["ar"] - lanes[ctx]["ar"]) < 1e-6 * r["ar"]
        assert abs(r["mtp"] - lanes[ctx]["mtp"]) < 1e-6 * r["mtp"]
    assert rec["campaign_binding"]["current"]
    assert rec["result_kind"].startswith("batch-SENSITIVITY")
