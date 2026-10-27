"""lec.py clock-gate -> enable abstraction (lane LEC-ICG 2026-10-26).
    python3 -m pytest -q tools/die_plan/test_lec_icg.py
Fixture examples/lec_icg: lec_icg_t.sv (two ASAP7 ICGx1 gates: async-reset, enabled, sync-reset registers and a
black-box clock pin on gated clocks) and its ORFS-image synthesis (make_netlists.sh): netlist_ok.v must be
EQUIVALENT with either gold frontend; the MUT_* netlists (inverted enable, register on the wrong gate, gated register
ungated) must be NOT EQUIVALENT; the REF_* netlists (cascaded gates, clock in the enable, falling-edge register on a
gated clock, gated clock into logic) are outside the abstraction and must be UNPROVEN, never EQUIVALENT."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

FX = HERE / "examples" / "lec_icg"


def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


needs_image = pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")


def _kit(tmp_path, netlist, synth_fe="slang"):
    k = tmp_path / Path(netlist).stem
    (k / "rtl").mkdir(parents=True)
    for f in ("lec_bbx.v", "lec_icg_t.sv"):
        shutil.copyfile(FX / f, k / "rtl" / f)
    n = k / "run" / "results" / "asap7" / "lec_icg_t" / "base"
    n.mkdir(parents=True)
    shutil.copyfile(FX / netlist, n / "1_2_yosys.v")
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_icg_t\nexport PLATFORM = asap7\n"
        "export VERILOG_FILES = /work/rtl/lec_bbx.v /work/rtl/lec_icg_t.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\n"
        f"export VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = {synth_fe}\nexport SYNTH_BLACKBOXES = lec_bbx\n")
    return k


def _run(kit):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900)
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


@needs_image
@pytest.mark.parametrize("synth_fe", ["slang", "verilog"])
def test_gated_core_is_equivalent(tmp_path, synth_fe):
    rc, r = _run(_kit(tmp_path, "netlist_ok.v", synth_fe))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["clock_gate_cells"] == ["ICGx1_ASAP7_75t_R"]
    for side in ("gold", "gate"):
        cg = r["clock_gates"][side]
        assert cg["gates"] == 2 and cg["gated_bb_clock_pins"] == 1, cg
        # ra, rb, rs: 3 x 4 bits (an ASAP7 liberty flop flattens to IQN + IQNN state cells: 2 per bit)
        assert cg["gated_flops"] == (12 if side == "gold" else 24), cg
    assert r["black_boxes"] == {"lec_bbx": 3}


@needs_image
@pytest.mark.parametrize("mut", ["MUT_INV_EN", "MUT_WRONG_GATE", "MUT_UNGATED"])
def test_clock_gate_mutants_are_not_equivalent(tmp_path, mut):
    rc, r = _run(_kit(tmp_path, f"netlist_{mut}.v"))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r


@needs_image
@pytest.mark.parametrize("ref,why", [("REF_CASCADE", "cascaded clock gates"),
                                     ("REF_CLK_IN_EN", "enable reads a clock net"),
                                     ("REF_NEGEDGE", "GCLK reaches"),
                                     ("REF_GCLK_LOGIC", "GCLK reaches")])
def test_uncovered_clock_gate_topologies_are_refused(tmp_path, ref, why):
    rc, r = _run(_kit(tmp_path, f"netlist_{ref}.v"))
    assert rc == 2 and r["verdict"] == "UNPROVEN" and why in r["reason"], r


def test_unknown_clock_gate_cell_stays_unsupported():
    assert lec.ICG_CELLS.match("ICGx1_ASAP7_75t_R") and lec.ICG_CELLS.match("ICGx8DC_ASAP7_75t_SL")
    assert lec.UNSUPPORTED_CELLS.match("ICGx9_ASAP7_75t_R") and not lec.ICG_CELLS.match("ICGx9_ASAP7_75t_R")
    assert not lec.ICG_CELLS.match("DHLx1_ASAP7_75t_R")


def _design(cells, ports):
    nb = {"hide_name": 0, "attributes": {}}
    return {"modules": {"lec_top": {"attributes": {"top": "00000000000000000000000000000001"}, "ports": ports,
                                    "cells": cells, "netnames": {"clk": dict(nb, bits=[2]), "en": dict(nb, bits=[3]),
                                                                 "u.q": dict(nb, bits=[6])}}}}


def _ff(t, **c):
    return {"type": t, "parameters": {}, "attributes": {}, "connections": {k: [v] for k, v in c.items()},
            "port_directions": {k: ("output" if k == "Q" else "input") for k in c}}


def test_sync_reset_over_enable_gated_flop_keeps_reset_inside_the_clock_enable(tmp_path):
    """$_SDFFE_ (sync reset over enable) on GCLK -> $_SDFFCE_ with CE = en & (R | E): reset stays clocked."""
    icg = {"type": "ICGx1_ASAP7_75t_R", "parameters": {}, "attributes": {},
           "connections": {"CLK": [2], "ENA": [3], "SE": ["0"], "GCLK": [5]},
           "port_directions": {"CLK": "input", "ENA": "input", "SE": "input", "GCLK": "output"}}
    ports = {"clk": {"direction": "input", "bits": [2]}, "en": {"direction": "input", "bits": [3]},
             "r": {"direction": "input", "bits": [4]}, "e": {"direction": "input", "bits": [7]},
             "d": {"direction": "input", "bits": [8]}}
    d = _design({"g": icg, "f": _ff("$_SDFFE_PN0P_", C=5, D=8, R=4, E=7, Q=6)}, ports)
    src, dst = tmp_path / "a.json", tmp_path / "b.json"
    src.write_text(json.dumps(d))
    st = lec.icg_to_enable(src, dst, "gold")
    m = json.loads(dst.read_text())["modules"]["lec_top"]
    f = m["cells"]["f"]
    assert f["type"] == "$_SDFFCE_PN0P_" and f["connections"]["C"] == [2] and "g" not in m["cells"]
    ce = f["connections"]["E"][0]
    types = {c["type"] for n, c in m["cells"].items() if n.startswith("$lec_icg$")}
    assert types == {"$_AND_", "$_OR_", "$_NOT_"} and ce != 7 and st["gated_flops"] == 1


# ---- S81-CORE-LAT-R7: post-hook netlist with a clock-gate COPY (core_infra ot_ci_tree_gate_copy), fixtures from
# make_copy_netlists.py: the copy on the same registered enable (through a tree buffer) is EQUIVALENT; a copy on
# another enable net or with SE tied high is NOT EQUIVALENT.
@needs_image
def test_clock_gate_copy_on_same_enable_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "netlist_COPY.v"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["clock_gates"]["gate"]["gates"] == 3 and r["clock_gates"]["gold"]["gates"] == 2, r["clock_gates"]


@needs_image
@pytest.mark.parametrize("mut", ["MUT_COPY_EN", "MUT_COPY_SE"])
def test_clock_gate_copy_mutants_are_not_equivalent(tmp_path, mut):
    rc, r = _run(_kit(tmp_path, f"netlist_{mut}.v"))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r
