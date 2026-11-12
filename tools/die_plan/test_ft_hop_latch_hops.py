"""HBM-VSN-XTAP-2 11-12 (DIE-HBM-100 option B): per-hop ft hop lockup list clock.ft_hop_lockup.hops {type: {slot: [k]}}.
A listed type latches ONLY the listed hops; unlisted hops are the plain station chain; the key absent (or another type
listed) is byte-identical to the type-level form.  Bound RTL proved by the strict bind verify (ot_dp_lk = 0 stages)."""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import schema as S  # noqa: E402
import test_ft_hop_lockup as T  # noqa: E402


def _raw(**kw):
    return {"clock": {"ft_hop_lockup": dict(types=["t"], **kw)}}


def test_helpers():
    assert S.ft_hop_latch_hops({}, "t") is None and S.ft_hop_latch_hops(_raw(), "t") is None
    r = _raw(hops={"t": {"L1": [2, 0, 2]}})
    assert S.ft_hop_latch_hops(r, "t") == {"L1": [0, 2]} and S.ft_hop_latch_hops(r, "u") is None
    assert S.ft_hop_latched(r, "t", "L1", 0) and S.ft_hop_latched(r, "t", "L1", 2)
    assert not S.ft_hop_latched(r, "t", "L1", 1) and not S.ft_hop_latched(r, "t", "L9", 0)
    assert S.ft_hop_latched(r, "u", "L1", 1) and S.ft_hop_latched(_raw(), "t", "L1", 5)
    assert not S.ft_hop_latched(_raw(hops={"t": {}}), "t", "L1", 0)     # listed with no hop = no latch


def test_schema():
    sch = S.SCHEMA["properties"]["clock"]["properties"]["ft_hop_lockup"]
    jsonschema.validate(_raw(hops={"t": {"L1": [0, 3]}})["clock"]["ft_hop_lockup"], sch)
    for bad in ({"t": {"L1": [-1]}}, {"t": {"L1": ["0"]}}, {"t": ["L1"]}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(_raw(hops=bad)["clock"]["ft_hop_lockup"], sch)
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk["properties"]["clock"]["properties"]["ft_hop_lockup"] == json.loads(json.dumps(sch))


def test_gen_rtl_loop_reads_the_list():
    src = (HERE / "gen_rtl.py").read_text()
    assert 'elif lk and not last and S.ft_hop_latched(P.raw, tn, s["name"], j):' in src


def _bind(tmp_path, lk):
    P = json.loads((T.EX / "die_plan_lanes.json").read_text())
    P["partition_types"]["tf"]["ft_slots"][0]["stations"] = 3
    P["latency"]["lanes"]["a0y"].update(cycles=5, stations=3)
    if lk is not None:
        P.setdefault("clock", {})["ft_hop_lockup"] = lk
    P["asbuilt"]["base"] = str(T.EX)
    tmp_path.mkdir(parents=True, exist_ok=True)
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(P))
    out = tmp_path / "o"
    rc = 0
    for c in ("elab", "bind", "verify"):
        rc = bind.main([c, str(pf), "--out", str(out), "--mem", "4"])
        if rc:
            break
    v = json.loads((out / "verify_report.json").read_text())
    assert rc == 0 and v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0, v.get("mismatches", [])[:3]
    return (out / "rtl" / "bt_tf.sv").read_text()


@pytest.mark.skipif(not T.HAVE_YOSYS, reason="no Yosys")
def test_bind_only_listed_hop_latched_and_absent_key_identical(tmp_path):
    slot = json.loads((T.EX / "die_plan_lanes.json").read_text())["partition_types"]["tf"]["ft_slots"][0]["name"]
    full = _bind(tmp_path / "a", {"types": ["tf"]})
    other = _bind(tmp_path / "b", {"types": ["tf"], "hops": {"zz": {slot: [0]}}})
    assert other == full                                       # another type listed: byte-identical
    one = _bind(tmp_path / "c", {"types": ["tf"], "hops": {"tf": {slot: [1]}}})
    assert one.count("ot_dp_lk #(.W(9))") == 1 and "u_fl_y_o_1" in one and "u_fl_y_o_0" not in one, one
    assert one.count("ot_dp_st #(.W(8))") == 3
    none = _bind(tmp_path / "d", {"types": ["tf"], "hops": {"tf": {}}})
    assert "ot_dp_lk" not in none and none.count("ot_dp_st #(.W(8))") == 3
