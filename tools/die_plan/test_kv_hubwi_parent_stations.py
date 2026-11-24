"""KV-HR-DEEPCLK 11-24: kv_hubwi_parent_stations (hub_Wi parent boundary stations + input lockup latches)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_hubwi_parent_stations as ps  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
HUB = REPO / "physical/die_plan/qwen_kvsys/bind/kv_host_wi"

WRAP_A = """module qkd_hr_a (ck, q_v, q_tag, q_rdy, i_d);
    input  wire ck;
    output wire [0:0] q_v;
    output wire [3:0] q_tag;
    output wire [0:0] q_rdy;
    input  wire [7:0] i_d;
endmodule
"""
PARENT = """module top (ck_a, x, y);
  qkd_hr_a host__qkd_hr_a (
    .ck(ck_a),
    .i_d({ \\g.p [3:0], y [3:0]}),
    .q_rdy(r),
    .q_tag(\\g.tag ),
    .q_v(\\g.v )
  );
  assign x = \\g.v ;
endmodule
"""


def _dir(tmp_path):
    (tmp_path / "wrappers_s/qkd_hr_a").mkdir(parents=True)
    (tmp_path / "wrappers_s/qkd_hr_a/qkd_hr_a.sv").write_text(WRAP_A)
    (tmp_path / "parent_src.sv").write_text(PARENT)
    return tmp_path


def test_station_and_latch(tmp_path):
    d = _dir(tmp_path)
    spec = {"stations": [{"inst": "host__qkd_hr_a", "prefixes": ["q_v", "q_tag"], "stages": 1}],
            "latches": [{"inst": "host__qkd_hr_a", "ports": ["i_d"]}]}
    (d / "parent_stations_spec.json").write_text(json.dumps(spec))
    assert ps.main(["--dir", str(d)]) == 0
    out = (d / "parent.sv").read_text()
    # the core pin drives the station input; the station drives the original net (all its loads move together)
    assert ".q_v(kvhw_st_qkd_hr_a__q_v)" in out
    assert "kvhw_dly #(.W(1), .D(1)) u_kvhw_st_qkd_hr_a__q_v (.clk(ck_a), .d(kvhw_st_qkd_hr_a__q_v), .q(\\g.v ));" in out
    assert "kvhw_dly #(.W(4), .D(1))" in out
    assert ".i_d(kvhw_lk_qkd_hr_a__i_d)" in out
    assert "kvhw_lk #(.W(8)) u_kvhw_lk_qkd_hr_a__i_d (.clk(ck_a), .d({ \\g.p [3:0], y [3:0]} ), .q(kvhw_lk_qkd_hr_a__i_d));" in out
    assert ".q_rdy(r)" in out and "assign x = \\g.v ;" in out
    rec = json.loads((d / "parent_stations.json").read_text())
    assert rec["declared_cycles"] == {"host__qkd_hr_a.q_tag": 1, "host__qkd_hr_a.q_v": 1}
    assert ps.main(["--dir", str(d), "--check"]) == 0
    (d / "parent.sv").write_text(out + "\n")
    assert ps.main(["--dir", str(d), "--check"]) == 1


@pytest.mark.parametrize("spec,why", [
    ({"stations": [{"inst": "host__nope", "prefixes": ["q_v"]}]}, "no such core instance"),
    ({"stations": [{"inst": "host__qkd_hr_a", "prefixes": ["zz_"]}]}, "match no output port"),
    ({"stations": [{"inst": "host__qkd_hr_a", "prefixes": ["q_rdy"]}]}, "ready / reset"),
    ({"latches": [{"inst": "host__qkd_hr_a", "ports": ["q_v"]}]}, "is an output"),
    ({"latches": [{"inst": "host__qkd_hr_a", "ports": ["nope"]}]}, "not a port"),
    ({}, "empty spec"),
])
def test_fail_closed(spec, why):
    ports = {"qkd_hr_a": WRAP_A}
    with pytest.raises(ps.GenError, match=why):
        ps.generate_text(PARENT, ports, spec)


def test_refuses_own_output(tmp_path):
    d = _dir(tmp_path)
    spec = {"stations": [{"inst": "host__qkd_hr_a", "prefixes": ["q_v"]}]}
    out, _ = ps.generate_text(PARENT, {"qkd_hr_a": WRAP_A}, spec)
    with pytest.raises(ps.GenError, match="already carries"):
        ps.generate_text(out, {"qkd_hr_a": WRAP_A}, spec)


@pytest.mark.skipif(not (HUB / "parent_src.sv").exists(), reason="hub_Wi parent not in this checkout's cone")
def test_hubwi_parent_current():
    """the checked-in kv3_hub_Wi parent is the generator's output for the checked-in spec and source"""
    assert ps.main(["--dir", str(HUB), "--check"]) == 0
    rec = json.loads((HUB / "parent_stations.json").read_text())
    kinds = [r["kind"] for r in rec["rows"]]
    assert kinds.count("latch") == 5 and kinds.count("station") >= 30
    assert not any(ps.NEVER.search(r["port"]) for r in rec["rows"])
