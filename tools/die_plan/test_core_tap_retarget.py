"""DIE-CORETAP-1119: core tap early offset := signed core latency - common latency, plan rows + die tree targets."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_tap_retarget as RT  # noqa: E402
import schema as S  # noqa: E402

PAIR = HERE / "examples" / "s81_pair" / "s81_pair_plan.json"
LIB = '''library(node) { time_unit : "1ps"; cell(node) { pin(clk) {
  direction : input;
  clock : true;
  timing() { timing_type : max_clock_tree_path;
    cell_rise(scalar) { values("VAL"); } cell_fall(scalar) { values("VAL"); }
  }
} } }'''


def signed(tt, ff):
    return dict(verdict="SIGNED", corners={c: dict(done=True, design="node", parasitics="spef", clock_ports=["clk"],
                                                   insertion_pinflops=dict(n=500, mean=m))
                                           for c, m in (("tt", tt), ("ff", ff))})


def fixture(tmp_path, sign=True, ins=(300.0, 240.0)):
    vd = tmp_path / "views" / "node"
    vd.mkdir(parents=True)
    (vd / "node_tt.lib").write_text(LIB.replace("VAL", "352.0"))
    (vd / "node_ff.lib").write_text(LIB.replace("VAL", "291.0"))
    if sign:
        (vd / "signoff.json").write_text(json.dumps(signed(330.5, 270.2)))
    raw = json.loads(PAIR.read_text())
    t = raw["partition_types"]["fa"]
    t["hard_cores"] = [dict(inst="u_c", module="node", lib=str(vd / "node_tt.lib"))]
    t["clock"].update(core_taps="early", taps=[dict(name="u_c.clk", kind="core", xy=[300.0, 900.0],
                                                   insertion_ps=ins[0], insertion_ff_ps=ins[1],
                                                   insertion_tol_ps=40.0)])
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(raw))
    return p


def test_rows_use_signed_mean_not_etm_max(tmp_path):
    p = fixture(tmp_path)
    _, rows, _, _ = RT.build_rows(p, tmp_path)
    (r,) = rows
    assert r["status"] == "CHANGE" and r["port"] == "clk_c0" and r["module"] == "node"
    assert (r["old_early_TT"], r["old_early_FF"]) == (50.0, 37.5)
    assert (r["new_ins_TT"], r["new_ins_FF"]) == (330.5, 270.2)
    assert r["new_early_TT"] == 80.5 and r["new_early_FF"] == pytest.approx(67.7)
    assert (r["etm_max_TT"], r["etm_max_FF"]) == (352.0, 291.0)
    _, rows, _, _ = RT.build_rows(p, tmp_path, basis="etm_max")
    assert rows[0]["new_early_TT"] == 102.0


def test_unsigned_core_keeps_declared(tmp_path):
    p = fixture(tmp_path, sign=False)
    _, rows, _, _ = RT.build_rows(p, tmp_path)
    assert rows[0]["status"] == "UNSIGNED" and rows[0]["new_early_TT"] == 50.0
    # signed-only rule: the ETM basis never moves an unsigned core either
    _, rows, _, _ = RT.build_rows(p, tmp_path, basis="etm_max")
    assert rows[0]["status"] == "UNSIGNED" and rows[0]["new_ins_TT"] == 300.0


def test_apply_feeds_schema_early_and_kit_sdc(tmp_path):
    import gen_phys as G
    p = fixture(tmp_path)
    _, rows, _, _ = RT.build_rows(p, tmp_path)
    raw = json.loads(p.read_text())
    assert RT.apply_rows(raw, rows) == 1
    P = S.Plan(raw)
    tp = P.types["fa"]["clock"]["taps"][0]
    assert S.core_tap_early_ps(P, tp) == 80.5            # die_clock --core-early pad / plan_tap_early read this
    assert "DIE-CORETAP-1119" in tp["note"]
    # kit side: the FF overlay the kit generator writes from the applied plan times the port at -new early
    ff = G.core_tap_ff_sdc(P, "fa")
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "core_taps_ff.sdc").write_text(ff)
    (kit / "constraint.sdc").write_text("set_clock_latency -source -clock clk -80.5000 [get_ports clk_c0]\n")
    res = RT.kit_check(kit, rows, "fa")
    assert [x[4] for x in res] == ["OK", "OK"]
    (kit / "constraint.sdc").write_text("set_clock_latency -source -clock clk -50.0000 [get_ports clk_c0]\n")
    assert [x[4] for x in RT.kit_check(kit, rows, "fa")] == ["MISTIMED", "OK"]
    assert RT.kit_check(kit, rows, "fa", offsets={"clk_c0": {}})[-1][4].startswith("RE-MEASURE")


def test_targets_and_shift_model(tmp_path):
    p = fixture(tmp_path)
    _, rows, P, _ = RT.build_rows(p, tmp_path)
    proof = tmp_path / "proof"
    proof.mkdir()
    (proof / "clk").mkdir()
    for c, late in (("TT", 1000.0), ("FF", 800.0)):
        taps = [dict(port="t_pfa__clk_t0", part="pfa", late_ps=late, early_ps=late - 50),
                dict(port="t_pfa__clk_t1", part="pfa", late_ps=late + 20, early_ps=late - 30),
                # die tree delivers the core tap only 10 ps early (plan 50, signed need 80.5)
                dict(port="t_pfa__clk_c0", part="pfa", late_ps=late, early_ps=late - 40)]
        (proof / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(corner=c, taps=taps)))
    tg = RT.tap_targets(rows, P, proof)
    e = tg["t_pfa__clk_c0"]
    assert e["TT"]["die_early"] == 10.0 and e["TT"]["target_early"] == 80.5 and e["TT"]["retarget_ps"] == 70.5
    tf = tmp_path / "tg.json"
    tf.write_text(json.dumps(dict(targets=tg)))
    out = tmp_path / "proof2"
    assert RT.main(["shift", str(proof), str(tf), "--out", str(out)]) == 0
    assert (out / "clk").is_symlink()
    t = {x["port"]: x for x in json.loads((out / "tap_arrivals_TT.json").read_text())["taps"]}
    assert t["t_pfa__clk_c0"]["late_ps"] == pytest.approx(1000.0 - 70.5)
    assert t["t_pfa__clk_t0"]["late_ps"] == 1000.0


def test_pairs_tag_unsigned_endpoints(tmp_path):
    p = fixture(tmp_path, sign=False)
    _, rows, P, _ = RT.build_rows(p, tmp_path)
    sta = {"corners": {"TT": {"classes": {"intra": {
        "worst_hold": {"launch": "t_pfa__clk_t0", "capture": "t_pfa__clk_c0"}, "worst_hold_slack_ps": -50.0,
        "worst_skew": [[60.0, "t_pfa__clk_c0", "t_pfa__clk_t1"]]}}}}}
    out = RT.pair_report(rows, sta, {"pfa": "fa", "pfb": "fb"})
    assert out[0][2] == "worst_hold" and out[0][6:] == ("regular", "UNSIGNED:node")
    assert out[1][6] == "UNSIGNED:node"


def test_late_target_region_local_and_record_signed(tmp_path):
    p = fixture(tmp_path, sign=False)
    sig = {"node": {"TT": 193.0, "FF": 160.0, "source": "view pack E2"}}
    _, rows, P, _ = RT.build_rows(p, tmp_path, signed_ins=sig)
    r = rows[0]
    assert r["status"] == "CHANGE" and r["signed_target_TT"] == -57.0 and r["new_early_TT"] == 0.0
    assert "view pack E2" in r["source"]
    proof = tmp_path / "proof"
    proof.mkdir()
    for c in ("TT", "FF"):
        taps = [dict(port="t_pfa__clk_t0", part="pfa", late_ps=1000.0), dict(port="t_pfa__clk_c0", part="pfa", late_ps=990.0)]
        (proof / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(taps=taps)))
    tg = RT.tap_targets(rows, P, proof, late=True)
    assert tg["t_pfa__clk_c0"]["TT"]["retarget_ps"] == -67.0          # deliver 57 ps late from 10 ps early
    assert RT.tap_targets(rows, P, proof, late=True, modules={"other"}) == {}
