#!/usr/bin/env python3
"""Prove the simulation-only ot_tkm_lt_live body equals the production keep-tree body (yosys SAT)."""
import re
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv"
SIM = ROOT / "rtl/test/hbm_layer/sim_compat/ot_tkm_lt_live_sim.sv"
WIDTHS = (1, 2, 3, 5, 8, 17, 64, 85)


def module_text(path, name):
    text = path.read_text()
    m = re.search(r"^\s*module\s+%s\b.*?^\s*endmodule\b" % name, text, re.S | re.M)
    assert m, f"{name} not found in {path}"
    return m.group(0)


def yosys():
    # The fleet build (0.68).  Old distro yosys (0.9) cannot parse the generate tree, so it is never used.
    for cand in (os.environ.get("OT_YOSYS"), Path.home() / ".local/opentallas-tools/bin/yosys"):
        if cand and Path(cand).exists():
            return str(cand)
    return None


def test_sim_body_equals_production(widths=WIDTHS):
    ys = yosys()
    if ys is None:
        print("SKIP: yosys not found")
        return
    gold = module_text(PROD, "ot_tkm_lt_live")
    sim = module_text(SIM, "ot_tkm_lt_live").replace("module ot_tkm_lt_live", "module ot_tkm_lt_live_sim", 1)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "gold.sv").write_text(gold + "\n")
        (tmp / "sim.sv").write_text(sim + "\n")
        for w in widths:
            script = "\n".join([
                f"read_verilog -sv {tmp / 'gold.sv'}", f"read_verilog -sv {tmp / 'sim.sv'}",
                f"chparam -set W {w} ot_tkm_lt_live ot_tkm_lt_live_sim", "proc", "flatten", "opt_clean",
                "miter -equiv -flatten -make_assert ot_tkm_lt_live ot_tkm_lt_live_sim miter",
                "hierarchy -top miter", "sat -verify -prove-asserts miter", ""])
            (tmp / f"eq{w}.ys").write_text(script)
            r = subprocess.run([ys, "-q", "-l", str(tmp / f"eq{w}.log"), str(tmp / f"eq{w}.ys")],
                               capture_output=True, text=True)
            log = (tmp / f"eq{w}.log").read_text()
            assert r.returncode == 0 and "SUCCESS" in log, f"W={w} not equivalent:\n{log[-2000:]}"
            print(f"W={w} EQUIVALENT")


def test_mutant_is_caught():
    """Control: a wrong body (a <= b) must fail the same proof."""
    ys = yosys()
    if ys is None:
        print("SKIP: yosys not found")
        return
    gold = module_text(PROD, "ot_tkm_lt_live")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "gold.sv").write_text(gold + "\n")
        (tmp / "mut.sv").write_text("module ot_tkm_lt_live_sim #(parameter integer W = 85) (input wire [W-1:0] a,"
                                    " input wire [W-1:0] b, output wire lt); assign lt = a <= b; endmodule\n")
        (tmp / "m.ys").write_text("\n".join([
            f"read_verilog -sv {tmp / 'gold.sv'}", f"read_verilog -sv {tmp / 'mut.sv'}",
            "chparam -set W 85 ot_tkm_lt_live ot_tkm_lt_live_sim", "proc", "flatten", "opt_clean",
            "miter -equiv -flatten -make_assert ot_tkm_lt_live ot_tkm_lt_live_sim miter",
            "hierarchy -top miter", "sat -verify -prove-asserts miter", ""]))
        r = subprocess.run([ys, "-q", "-l", str(tmp / "m.log"), str(tmp / "m.ys")], capture_output=True, text=True)
        assert r.returncode != 0, "mutant a<=b was not caught"
        print("mutant a<=b caught")


if __name__ == "__main__":
    test_sim_body_equals_production()
    test_mutant_is_caught()
    print("PASS")
