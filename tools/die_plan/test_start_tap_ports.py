"""G0 START tap ports (C-START-TAP-PORT-MISSING): missing-port fixture fails, clean control passes."""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check as C
import start_tap_ports as T


def _stages(tmp, ids, gz=False):
    doc = dict(schema="ot_start_stages/1", stages=[dict(id=i, region=f"st:{i}", clock_port=f"t_st_{i}__clk") for i in ids])
    p = tmp / ("start_stages.json.gz" if gz else "start_stages.json")
    (gzip.open(p, "wt") if gz else open(p, "w")).write(json.dumps(doc))
    return p


def _ctree(tmp, ports, name="ctree.v"):
    p = tmp / name
    p.write_text("// c\nmodule die_ctree (root, " + ", ".join(ports) + ");\n  input root;\n"
                 + "".join(f"  output {x};\n" for x in ports) + "endmodule\n")
    return p


def test_missing_port_is_blocking_error_naming_stage_and_port(tmp_path):
    ss = _stages(tmp_path, ["b0", "r1_1", "r2_1"])
    ct = _ctree(tmp_path, ["t_sp3__clk", "t_st_b0__clk"])
    R = C.Report()
    rec = T.check({}, R, start_stages=str(ss), die_ctree=str(ct))
    errs = R.errors()
    assert len(errs) == 2 and rec["missing_count"] == 2 and rec["required"] == 3
    assert all(e["check"] == "start_tap_ports" for e in errs)
    assert "t_st_r1_1__clk" in errs[0]["msg"] and "r1_1" in errs[0]["msg"] and "START stage" in errs[0]["msg"]


def test_clean_control_passes(tmp_path):
    ss = _stages(tmp_path, ["b0", "r1_1"], gz=True)
    ct = _ctree(tmp_path, ["t_st_b0__clk", "t_st_r1_1__clk", "t_sp3__clk"])
    R = C.Report()
    rec = T.check({}, R, start_stages=str(ss), die_ctree=str(ct))
    assert R.items == [] and rec["missing_count"] == 0 and rec["required"] == 2


def test_many_missing_are_counted_not_flooded(tmp_path):
    ss = _stages(tmp_path, [f"x{i}" for i in range(50)])
    ct = _ctree(tmp_path, ["t_sp3__clk"])
    R = C.Report()
    T.check({}, R, start_stages=str(ss), die_ctree=str(ct), max_msgs=5)
    assert len(R.errors()) == 6 and "45 more" in R.errors()[-1]["msg"]


def test_no_ctree_is_warn_not_silent(tmp_path):
    ss = _stages(tmp_path, ["b0"])
    R = C.Report()
    T.check({}, R, start_stages=str(ss))
    assert not R.errors() and len(R.items) == 1 and R.items[0]["level"] == "WARN" and "UNVERIFIED" in R.items[0]["msg"]


def test_plan_provider_nodes_and_plandir_autodiscovery(tmp_path):
    raw = dict(clock=dict(landing_network=dict(start_tree=dict(provider=dict(nodes=[dict(id="b0", clock_port="t_st_b0__clk")])))))
    _ctree(tmp_path, ["t_sp3__clk"])
    R = C.Report()
    T.check(raw, R, plan_dir=str(tmp_path))      # PLANDIR/ctree.v found
    assert len(R.errors()) == 1
    d = tmp_path / "NF" / "plan"
    d.mkdir(parents=True)
    pv = tmp_path / "NF" / "provider_e1"
    pv.mkdir()
    _stages(pv, ["b0"], gz=True)
    _ctree(d, ["t_st_b0__clk"])
    R2 = C.Report()
    rec = T.check({}, R2, plan_dir=str(d))
    assert R2.items == [] and rec["required"] == 1


def test_no_start_stages_no_finding(tmp_path):
    R = C.Report()
    rec = T.check({}, R, plan_dir=str(tmp_path))
    assert R.items == [] and rec["required"] == 0
