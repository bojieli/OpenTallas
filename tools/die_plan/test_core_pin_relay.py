"""CORE-PIN-RELAY-1930: relay stages and landing flops seated at hard-core pins (all dies, opt-in plan key core_pin_relay).
gen_phys exports, relay_depth pin stations, schema keys, the relay_mid.tcl PIN form and core_out_land.tcl IN side.
The OpenROAD cases need docker + openroad/orfs:asap7lock (skipped otherwise).
python3 -m pytest -q tools/die_plan/test_core_pin_relay.py"""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
import gen_phys  # noqa: E402
import relay_depth as RD  # noqa: E402
import schema  # noqa: E402


def _clean(monkeypatch):
    for k in ("OT_CORE_PIN_RELAY", "OT_RELAY_MID_FIT", "OT_CORE_OUT_LAND"):
        monkeypatch.delenv(k, raising=False)


def test_absent_is_byte_identical(monkeypatch):
    _clean(monkeypatch)
    assert gen_phys._core_pin_relay({}, "col_h9_r1__t1") is None
    assert gen_phys._core_pin_relay_exports({}, "col_h9_r1__t1") == []


def test_plan_key_per_type_and_plan_wide(monkeypatch):
    _clean(monkeypatch)
    b = {"core_pin_relay_types": ["col_h9_r1"]}
    assert gen_phys._core_pin_relay(b, "col_h9_r1__t1__cl49d7a23e")["w"] == 0.1
    assert gen_phys._core_pin_relay(b, "col_h9_r0_p2__t1") is None
    ex = gen_phys._core_pin_relay_exports({"core_pin_relay": {"re": "_u_t[0-9]+$", "w": 0.2, "hop_um": 250}}, "x")
    assert ex == ["export OT_RELAY_MID_PIN = _u_t[0-9]+$$=0.2", "export OT_RELAY_MID_PIN_HOP_UM = 250",
                  "export OT_CORE_IN_LAND = 1"]


def test_env_pilot_and_bad_values(monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("OT_CORE_PIN_RELAY", "1")
    c = gen_phys._core_pin_relay({}, "cbn_q01")
    assert c["re"] == "." and c["hop_um"] > 0
    for bad in ({"core_pin_relay": {"w": 1.5}}, {"core_pin_relay": {"re": "a b"}}):
        monkeypatch.delenv("OT_CORE_PIN_RELAY", raising=False)
        with pytest.raises(ValueError):
            gen_phys._core_pin_relay(bad, "t")


def test_pin_stations_add_cycles_only_over_the_limit():
    # 1,032 um core -> core: midpoint model 3 stations (4 hops of 258), pin seats 5 (30 + 4 x 243 + 30)
    assert RD.stations_needed(1032, 300) == 3
    assert RD.pin_stations(1032, 300, 1.0, 1.0, 0.1) == 5
    # a short core-to-core wire is a hop: no stage, with or without pin seats
    assert RD.pin_stations(250, 300, 1.0, 1.0, 0.1) == 0
    # HALF weights stay the lower bound
    assert RD.pin_stations(900, 300, 0.05, 1.0, 0.1) == RD.stations_needed(900, 300, 0.05, 0.1)
    assert RD.pin_stations(900, 300, 1.0, 1.0, None) == RD.stations_needed(900, 300)


def test_pin_weight_from_plan():
    assert RD.pin_weight({"budgets": {}}, "t") is None
    assert RD.pin_weight({"budgets": {"core_pin_relay": True}}, "t") == 0.1
    assert RD.pin_weight({"budgets": {"core_pin_relay": {"w": 0.2}}}, "t") == 0.2
    assert RD.pin_weight({"budgets": {"core_pin_relay_types": ["col_h9_r1"]}}, "col_h9_r1__t1") == 0.1
    assert RD.pin_weight({"budgets": {}}, "t", 0.15) == 0.15


def test_schema_keys_on_disk():
    b = schema.SCHEMA["properties"]["budgets"]["properties"]
    assert "core_pin_relay" in b and "core_pin_relay_types" in b
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk["properties"]["budgets"]["properties"]["core_pin_relay"] == b["core_pin_relay"]
    tcl = (HERE / "relay_mid.tcl").read_text()
    assert "OT_RELAY_MID_PIN" in tcl and "proc rm_pin_list" in tcl
    assert "OT_CORE_IN_LAND" in (HERE / "core_out_land.tcl").read_text()


# ---------------------------------------------------------------------------------------------- OpenROAD (docker)
FF, BUF = "DFFHQNx1_ASAP7_75t_R", "BUFx2_ASAP7_75t_R"
# two macros 900 um apart; a 3-stage relay chain u_y_a_{0,1,2} from u_m0 rd_out[0] to u_m1 wd_in[0]; a 1-stage chain
# u_y_b_0 on bit 1 (too few stages to seat both ends at a 300-um cap); flop drv feeds u_m1 wd_in[2] only (IN side)
NET = f"""module t(input wire clk, input wire a);
  wire [20:0] q; wire [20:0] w; wire s0, s1, n0, n1, b0, b1, d0;
  fakeram7_64x21 u_m0 (.clk(clk), .rd_out(q));
  fakeram7_64x21 u_m1 (.clk(clk), .wd_in(w));
  {FF} \\u_y_a_0.r  (.CLK(clk), .D(q[0]), .QN(s0));
  {FF} \\u_y_a_1.r  (.CLK(clk), .D(s0), .QN(s1));
  {FF} \\u_y_a_2.r  (.CLK(clk), .D(s1), .QN(w[0]));
  {FF} \\u_y_b_0.r  (.CLK(clk), .D(q[1]), .QN(w[1]));
  {FF} drv (.CLK(clk), .D(a), .QN(d0));
  {BUF} bd (.A(d0), .Y(w[2]));
endmodule
"""

TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $P/fakeram7_64x21.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 1400 600" -core_area "5 5 1395 595" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach i [$blk getInsts] {
  if {[$i getName] eq "u_m0"} { $i setLocation [expr {100 * $u}] [expr {200 * $u}]; $i setPlacementStatus FIRM; continue }
  if {[$i getName] eq "u_m1"} { $i setLocation [expr {1000 * $u}] [expr {200 * $u}]; $i setPlacementStatus FIRM; continue }
  $i setLocation [expr {700 * $u}] [expr {500 * $u}]; $i setPlacementStatus PLACED
}
set ::env(RESULTS_DIR) /w
source /w/relay_mid.tcl
source /w/core_out_land.tcl
foreach i [$blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  lassign [$i getLocation] x y
  puts "CHK [string map {\\ {}} [$i getName]] [expr {$x / double($u)}] [expr {$y / double($u)}] [$i getPlacementStatus]"
}
foreach {m p} {u_m0 rd_out[0] u_m1 wd_in[0] u_m1 wd_in[2]} {
  lassign [[[$blk findInst $m] findITerm $p] getAvgXY] ok px py
  puts "PIN $m.$p [expr {$px / double($u)}] [expr {$py / double($u)}]"
}
"""


def _run(env):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(NET)
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "relay_mid.tcl", d)
        shutil.copy(HERE / "core_out_land.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        e = []
        for k, v in env.items():
            e += ["-e", f"{k}={v}"]
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", *e, "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=900)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        return r.stdout + r.stderr


def _parse(out):
    pos = {n: (float(x), float(y), st) for n, x, y, st in re.findall(r"CHK (\S+) ([0-9.]+) ([0-9.]+) (\w+)", out)}
    pins = {n: (float(x), float(y)) for n, x, y in re.findall(r"PIN (\S+) ([0-9.]+) ([0-9.]+)", out)}
    return pos, pins


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


BASE = {"OT_RELAY_MID_RE": r"^(.*u_y_[a-z]+_[0-9]+)[.]", "OT_RELAY_MID_FIT": "1", "OT_RELAY_MID_MIN_UM": "100"}


@pytest.mark.skipif(not shutil.which("docker"), reason="no docker")
def test_pin_form_seats_chain_ends_and_keeps_short_chains():
    off = _run(BASE)
    pos0, pins = _parse(off)
    assert "OT_RELAY_MID_PIN" not in off, off[-3000:]
    on = _run(dict(BASE, OT_RELAY_MID_PIN=".=0.1", OT_RELAY_MID_PIN_HOP_UM="420", OT_CORE_IN_LAND="1"))
    pos, pins = _parse(on)
    assert "OT_RELAY_MID_PIN seated chains: both ends 1" in on, on[-4000:]
    src, snk = pins["u_m0.rd_out[0]"], pins["u_m1.wd_in[0]"]
    # 3 stages over ~900 um: both ends within ~45 um of their pins (halo 8.64 + FIT margin), never farther than before
    assert _d(pos["u_y_a_0.r"][:2], src) < 60 and _d(pos["u_y_a_2.r"][:2], snk) < 60, (pos, pins)
    assert _d(pos["u_y_a_0.r"][:2], src) < _d(pos0["u_y_a_0.r"][:2], src)
    # the 1-stage chain cannot seat an end within the cap: unchanged point
    assert abs(pos["u_y_b_0.r"][0] - pos0["u_y_b_0.r"][0]) < 3, (pos["u_y_b_0.r"], pos0["u_y_b_0.r"])
    # IN side: the single-load driver of u_m1 wd_in[2] sits at that pin, FIRM
    assert "OT_CORE_IN_LAND placed 1 " in on, on[-3000:]
    assert _d(pos["drv"][:2], pins["u_m1.wd_in[2]"]) < 40 and pos["drv"][2] == "FIRM"
