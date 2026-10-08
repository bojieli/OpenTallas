#!/usr/bin/env python3
"""Build the exact native head glue with 56 real hardened delay leaves.

This is the native numerical interface, not the S81 transport placeholder ABI.
The 0.2-period IO budget is a conditional standalone contract.
Run only in a pinned clean worktree through the compute host admission guard.
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VIEW = "physical/s81_die_views/hbglue"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--nickname", default="native_hier_clockeco")
    a = ap.parse_args()
    cmd = [sys.executable, str(ROOT / "tools/run_abi3_physical.py"),
           "--view", "asap7", "--top", "ot_dsrom_head_bundle_glue",
           "--source", "rtl/s81/ot_dsrom_head_bundle_glue.sv",
           "--source", "rtl/hdc/ot_hdc_delay.sv",
           "--param", "USE_HARD_DELAY8=1",
           "--macro-view", f"ot_s81_head_delay8x32={VIEW}/ot_s81_head_delay8x32",
           "--macro-place-halo", "1", "1",
           "--die-area", "0", "0", "300", "150",
           "--core-area", "4.32", "4.32", "295.68", "145.68",
           "--clock-period-ns", ".833", "--clock-uncertainty-ns", ".060",
           "--clock-uncertainty-hold-ns", ".025",
           "--orfs-corner", "WC", "--hold-corners", "WC,BC",
           "--stages", "pnr", "--io-delay-fraction", ".2",
           "--synth-timeout-seconds", "unlimited",
           "--flow-timeout-seconds", "unlimited",
           "--keep-workdir", str(a.work.resolve()), "--output", str(a.output.resolve()),
           "--orfs-var", f"PDN_TCL=/src/{VIEW}/parent_pdn.tcl",
           "--orfs-var", f"MACRO_PLACEMENT_TCL=/src/{VIEW}/parent_macros.tcl",
           "--orfs-var", "DETAIL_PLACEMENT_ARGS=-use_diamond_legalizer",
           "--orfs-var", "PLACE_DENSITY_LB_ADDON=", "--place-density", ".60",
           "--routing-layers", "M2", "M6", "--orfs-var", "ADDER_MAP_FILE=",
           "--max-transition-ns", ".25", "--orfs-var", "NUM_CORES=16",
           "--orfs-var", "CTS_SNAPSHOTS=1",
           "--nickname-tag", a.nickname, "--keep-heavy-artifacts"]
    for hook, name in [
        ("POST_PDN", "parent_macro_obstructions"),
        ("PRE_GLOBAL_PLACE_SKIP_IO", "parent_row_place"),
        ("PRE_GLOBAL_PLACE", "parent_row_place"),
        ("PRE_CTS", "parent_clock_topology"),
        ("PRE_GLOBAL_ROUTE", "parent_diamond"),
    ]:
        cmd += ["--step-tcl", f"{hook}={VIEW}/{name}.tcl"]
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
