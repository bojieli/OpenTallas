#!/usr/bin/env python3
"""HBM-CTS-LEAFSLEW (DIE-HBM-59 11-03) stage-resume helper: install the default-on clk_leaf_repeat POST_CTS hook into an
EXISTING HBM core kit (generated before the class fix) exactly as gen_core_kit_hbm.py now does for new kits: copy
clk_leaf_repeat.tcl, append `override export POST_CTS_TCL = /work/clk_leaf_repeat.tcl` + OT_CLR_NEXT_TCL = the kit's
effective POST_CTS hook to config.mk (idempotent; refused for a plan-built core tree).  Then rerun the kit from CTS
(4_*: run_kit_hbm.sh KIT finish with 1_*/2_*/3_* results kept) - no rebuild, gates unchanged.

    python3 clk_leaf_resume.py KIT_DIR [--max-um 50] [--max-fanout 12]
"""
import argparse, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _gen():
    spec = importlib.util.spec_from_file_location("gen_core_kit_hbm_clr", HERE / "gen_core_kit_hbm.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def apply(kd, max_um=None, max_fanout=None):
    kd = Path(kd); g = _gen()
    cfgp = kd / "config.mk"
    lines = cfgp.read_text().splitlines()
    before = len(lines)
    r = g.clk_leaf_repeat_hook(kd, lines)
    if r.get("installed") and len(lines) > before:
        add = ["", "# ---- HBM-CTS-LEAFSLEW stage-resume (clk_leaf_resume.py): POST_CTS clock level/leaf repeaters"] + lines[before:]
        if max_um is not None: add.append(f"export OT_CLK_LEAF_MAX_UM = {max_um:g}")
        if max_fanout is not None: add.append(f"export OT_CLK_LEAF_MAX_FANOUT = {int(max_fanout)}")
        cfgp.write_text("\n".join(lines[:before] + add) + "\n")
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit"); ap.add_argument("--max-um", type=float); ap.add_argument("--max-fanout", type=int)
    a = ap.parse_args()
    print(json.dumps(apply(a.kit, a.max_um, a.max_fanout)))
