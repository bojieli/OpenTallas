"""GENDRY-STOPITER-1124 (KV-OWN-HUB-R2, COORD): PRE GENDRY kv3_hub_Eo / kv3_hub_Wo died on a bare StopIteration in landing_place.tcl
(A5t3 unchanged): the dry gen had no --clock-landing (no <plan dir>/source_sidecar.json in a KV plan dir), so no collector event was
installed and the local source was looked up in the captured native reset solve.  The dry gen now takes the as-built's
clock_landing_table like the wave; a source with no relay is a named LANDING-SOURCE-UNMODELED stop, reported WARN GENDRY-UNMODELED."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_place as LP  # noqa: E402
import plan_gate_pre as P  # noqa: E402


class _Plan:
    """kv3_hub_Eo form: contract collector_tree = the captured native reset solve (u_rrl_*), no collector_event"""
    def __init__(self, event=None):
        native = {"root": [10.0, 10.0], "relays": [{"q": "u_rrl_0", "d": "rst_root_n", "xy": [20.0, 20.0]},
                                                   {"q": "u_rrl_1", "d": "u_rrl_0", "xy": [30.0, 30.0]}]}
        c = {"bands": {}, "pins": [], "collector_root_node": "rst_root_n", "collector_tree": native,
             "collector_local_sources": [{"name": "i_rst_sq", "tap": 5, "xy_um": [40.0, 40.0]}], "collector_children": []}
        if event:
            c["collector_event"] = event
        self.types = {"kv3_hub_Eo": {"clock": {"landing_contract": c}}}


def test_native_solve_tree_is_a_named_stop_not_stopiteration():
    with pytest.raises(LP.LandingSourceUnmodeled) as ei:
        LP.tcl(_Plan(), "kv3_hub_Eo")
    msg = str(ei.value)
    assert not isinstance(ei.value, StopIteration)
    assert msg.startswith("LANDING-SOURCE-UNMODELED type kv3_hub_Eo") and "rst_n_t5" in msg and "2 relays" in msg
    assert "no collector_event installed" in msg and "--clock-landing" in msg


def test_sidecar_event_tree_places_the_source():
    ev = {"tree": {"root": [10.0, 10.0], "relays": [{"q": "rst_n_t5", "d": "rst_root_n", "xy": [33.0, 44.0]}]},
          "collector_root_node": "rst_root_n", "local_sources": [{"name": "i_rst_sq", "tap": 5, "xy_um": [40.0, 40.0]}],
          "children": []}
    assert "u_cland_rst_i_rst_sq" in LP.tcl(_Plan(ev), "kv3_hub_Eo")


def _plans(tmp, ab_rel="physical/die_plan/kv/plan_of_record/eW_sidecar_A5t3.json"):
    pd = tmp / "physical/die_plan/kv/plan_of_record"
    pd.mkdir(parents=True)
    (tmp / ab_rel).write_text("{}")
    ab = pd / "asbuilt_allfix_A5t3.json"
    ab.write_text(json.dumps({"base": "../../../..", "clock_landing_table": ab_rel}))
    pb, pn = pd / "base.json", pd / "plan.json"
    pb.write_text(json.dumps({"partition_types": {"kv3_hub_Eo": {"x": 1}}}))
    pn.write_text(json.dumps({"partition_types": {"kv3_hub_Eo": {"x": 2}}}))
    return pn, pb, ab, tmp / ab_rel


def test_dry_gen_takes_the_asbuilt_sidecar_like_the_wave(tmp_path):
    pn, pb, ab, sc = _plans(tmp_path)
    assert P.gendry_sidecar(tmp_path, pn, asbuilt=ab) == (str(sc.absolute()), "as-built clock_landing_table (as the wave)")
    assert P.gendry_sidecar(tmp_path, pn, sidecar="/x.json", asbuilt=ab)[0] == "/x.json"
    seen = []

    def runner(cmd, cwd, timeout):
        seen.append(cmd)
        return 0, ""
    out = P.check_gendry(tmp_path, pn, pb, env={"OT_PRE_KIT_RTL_MODE": "plan"}, runner=runner, asbuilt=ab)
    gen = [c for c in seen if "phys" in c][0]
    assert gen[gen.index("--clock-landing") + 1] == str(sc.absolute())
    assert not [x for x in out if x.startswith("FAIL")] and "as the wave" in out[-1]


def test_unmodeled_stop_is_warn_not_fail(tmp_path):
    pn, pb, ab, _ = _plans(tmp_path)

    def runner(cmd, cwd, timeout):
        return 1, ("Traceback (most recent call last):\n  File \"landing_place.py\", line 931, in tcl\n"
                   "landing_place.LandingSourceUnmodeled: LANDING-SOURCE-UNMODELED type kv3_hub_Eo: local source i_rst_sq node "
                   "rst_n_t5 is no relay of the contract collector_tree (2 relays)\n")
    out = P.check_gendry(tmp_path, pn, pb, env={"OT_PRE_KIT_RTL_MODE": "plan"}, runner=runner, asbuilt=ab)
    assert not [x for x in out if x.startswith("FAIL")], out
    w = [x for x in out if x.startswith("WARN GENDRY-UNMODELED kv3_hub_Eo: LANDING-SOURCE-UNMODELED")]
    assert len(w) == 1 and "rst_n_t5" in w[0]
