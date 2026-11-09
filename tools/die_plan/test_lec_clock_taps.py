"""DIE-HEAD-91 11-09: lec.py clock-tap tie model (clock_tap_ties + wrapper_verilog ties), pure python.
    python3 -m pytest -q tools/die_plan/test_lec_clock_taps.py
The real-netlist proof (S81 HEAD hd_tile vH12a routed 6_final.v: positive EQUIVALENT, tie-off control 20 differs,
ft-pin data / constant / inverted / undeclared-port / tap-into-data mutants all caught) is in the READY post."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

PORTS = [("clk", "input", 1, 0), ("clk_t1", "input", 1, 0), ("clk_t2", "input", 1, 0), ("fclk_in_i", "input", 1, 0),
         ("i", "input", 8, 0), ("o", "output", 4, 0)]


def kit(tmp_path, taps, sdc):
    (tmp_path / "budget.json").write_text(json.dumps({"clock": {"taps": [{"name": t, "kind": "density"} for t in taps]}}))
    (tmp_path / "constraint.sdc").write_text(sdc)
    return tmp_path


def test_ties_declared_taps_of_one_create_clock(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_LEC_TAP_TIE", raising=False)
    k = kit(tmp_path, ["clk", "clk_t1", "clk_t2"],
            "create_clock -name clk -period 833 [get_ports {clk clk_t1 clk_t2}]\n"
            "create_clock -name fclk_in_i -period 833 [get_ports fclk_in_i]\n")
    r = lec.clock_tap_ties(k, PORTS)
    assert r["root"] == "clk" and r["clock"] == "clk" and r["ports"] == ["clk_t1", "clk_t2"] and r["untied"] == []
    v = lec.wrapper_verilog("top", PORTS, ties={p: r["root"] for p in r["ports"]})
    assert ".clk_t1(clk)" in v and ".clk_t2(clk)" in v and ".fclk_in_i(fclk_in_i)" in v and ".clk(clk)" in v
    assert "input clk_t1;" in v                     # the wrapper input stays declared, unloaded


def test_no_taps_no_model(tmp_path):
    assert lec.clock_tap_ties(kit(tmp_path, ["clk"], "create_clock -name clk -period 833 [get_ports clk]\n"),
                              PORTS) is None
    assert lec.clock_tap_ties(tmp_path / "missing", PORTS) is None
    assert ".clk_t1(clk_t1)" in lec.wrapper_verilog("top", PORTS)


def test_fail_closed_cases(tmp_path):
    # a tap outside the root's create_clock, a tap with a generated clock, a bus tap, a tap that is not a port
    ports = PORTS + [("clk_t3", "input", 2, 0)]
    k = kit(tmp_path, ["clk", "clk_t1", "clk_t2", "clk_t3", "clk_t9"],
            "create_clock -name clk -period 833 [get_ports {clk clk_t1 clk_t3 clk_t9}]\n"
            "create_generated_clock -name g -source [get_ports clk] -divide_by 1 [get_ports clk_t1]\n")
    r = lec.clock_tap_ties(k, ports)
    why = {u["port"]: u["why"] for u in r["untied"]}
    assert r["ports"] == [] and set(why) == {"clk_t1", "clk_t2", "clk_t3", "clk_t9"}
    assert "generated" in why["clk_t1"] and "root's create_clock" in why["clk_t2"]
    assert "2 bits" in why["clk_t3"] and "not a top input" in why["clk_t9"]


def test_taps_split_over_two_clocks_tie_nothing(tmp_path):
    k = kit(tmp_path, ["clk", "clk_t1"], "create_clock -name clk -period 833 [get_ports clk]\n"
                                         "create_clock -name c1 -period 833 [get_ports clk_t1]\n")
    r = lec.clock_tap_ties(k, PORTS)
    assert r["ports"] == [] and r["root"] is None and len(r["untied"]) == 2


def test_tap_in_two_create_clocks_ties_nothing(tmp_path):
    k = kit(tmp_path, ["clk", "clk_t1", "clk_t2"], "create_clock -name clk -period 833 [get_ports {clk clk_t1 clk_t2}]\n"
                                                   "create_clock -name x -period 900 -add [get_ports clk_t2]\n")
    r = lec.clock_tap_ties(k, PORTS)
    assert r["ports"] == [] and r["root"] is None and len(r["untied"]) == 3


def test_env_off(tmp_path, monkeypatch):
    k = kit(tmp_path, ["clk", "clk_t1"], "create_clock -name clk -period 833 [get_ports {clk clk_t1}]\n")
    monkeypatch.setenv("OT_LEC_TAP_TIE", "0")
    assert lec.clock_tap_ties(k, PORTS) is None


def test_generated_clock_source_tap_stays_tied(tmp_path):
    # hd_tile: create_generated_clock -name fclk_out_o -master_clock clk -source [get_ports clk_t26] ... [get_ports fclk_out_o]
    k = kit(tmp_path, ["clk", "clk_t1", "clk_t2"],
            "create_clock -name clk -period 833 [get_ports {clk clk_t1 clk_t2}]\n"
            "create_generated_clock -name o -master_clock clk -source [get_ports clk_t2] -divide_by 1 [get_ports o]\n")
    assert lec.clock_tap_ties(k, PORTS)["ports"] == ["clk_t1", "clk_t2"]


def test_backslash_continued_sdc(tmp_path):
    k = kit(tmp_path, ["clk", "clk_t1"], "create_clock -name clk -period 833 \\\n  [get_ports {clk clk_t1}]\n")
    assert lec.clock_tap_ties(k, PORTS)["ports"] == ["clk_t1"]


def test_tap_tie_switch_reaches_the_container(monkeypatch, tmp_path):
    # the 02:1x control run: OT_LEC_TAP_TIE=0 on the host was not forwarded by via_docker, so the image tied anyway
    import types
    seen = {}
    monkeypatch.setenv("OT_LEC_TAP_TIE", "0")
    monkeypatch.setattr(lec.subprocess, "run", lambda cmd, **kw: seen.setdefault("cmd", cmd) and types.SimpleNamespace(returncode=0))
    a = types.SimpleNamespace(kit=str(tmp_path), out=str(tmp_path / "o"), conflicts=1, jobs=1, netlist=None, reuse=False,
                              gold_frontend=None, hints=None, port_map=None)
    lec.via_docker(a, "img", 1)
    assert "OT_LEC_TAP_TIE=0" in " ".join(map(str, seen.get("cmd", [])))
