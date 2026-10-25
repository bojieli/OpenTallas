#!/usr/bin/env python3
"""S81-HEAD (10-24): install a rebuilt head element view (tools/s81_head/hd_elemA_rebuild.py kit, routed + signoff.py)
into physical/die_plan/s81_head/cores/views_rb/<top>/: <top>.lef (the routed abstract), <top>_tt.lib / <top>_ff.lib
(the kit's post-route timing models), MANIFEST.json (kit, signoff verdict + numbers, sha256 of every file, the kit's
early core tap and the lib max_clock_tree_path).  Refuses a kit whose signoff/signoff.json is not SIGNED unless --out
points outside the repo views_rb or --preview is given (geometry previews only; never commit those).

Core-latency contract (BRIEFING decision 5e): the element was signed with clk source latency -early (kit SDC), i.e. the
tile delivers its clock `early` ps before the common latency.  gen_plan.py reads `early_core_tap_ps` from this
MANIFEST for the core tap (insertion = common + early); the lib's max_clock_tree_path (max over ALL internal flops)
is recorded for information.

    python3 tools/s81_head/hd_views_rb.py KIT [--out DIR]
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
VRB = R / "physical/die_plan/s81_head/cores/views_rb"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lib_ctp(p):
    t = p.read_text()
    m = re.search(r'timing_type\s*:\s*max_clock_tree_path\s*;.*?values\("([-0-9.]+)"\)', t, re.S)
    return float(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("--out", help="views root (default the repo views_rb)")
    ap.add_argument("--preview", action="store_true", help="install an UNSIGNED view for a geometry preview (never commit)")
    a = ap.parse_args()
    K = Path(a.kit).resolve()
    rb = json.loads((K / "rebuild.json").read_text())
    top = rb["top"]
    so = json.loads((K / "signoff/signoff.json").read_text())
    root = Path(a.out).resolve() if a.out else VRB
    if so.get("verdict") != "SIGNED" and root == VRB.resolve() and not a.preview:
        sys.exit(f"{K}: signoff verdict {so.get('verdict')}: not installing into {VRB} (use --out for a preview)")
    lefs = sorted(K.glob(f"run/results/asap7/*/base/{top}.lef"))
    assert len(lefs) == 1, lefs
    src = {f"{top}.lef": lefs[0], f"{top}_tt.lib": K / f"views/{top}_tt.lib", f"{top}_ff.lib": K / f"views/{top}_ff.lib"}
    d = root / top
    d.mkdir(parents=True, exist_ok=True)
    files = {}
    for n, s in src.items():
        shutil.copyfile(s, d / n)
        files[n] = dict(source=str(s), sha256=sha(d / n))
    ck = so.get("checks", {})
    man = dict(tool="tools/s81_head/hd_views_rb.py", kit=str(K), rebuild=rb,
               signoff=dict(verdict=so.get("verdict"), reasons=so.get("reasons", []),
                            setup_tt_ps=ck.get("setup_tt", {}).get("wns_ps"), hold_ff_ps=ck.get("hold_ff", {}).get("wns_ps"),
                            clock=ck.get("clock", {}).get("by_corner"), drc=ck.get("drc", {}).get("count"),
                            antenna=ck.get("antenna", {}).get("count"), generated=so.get("generated")),
               early_core_tap_ps=rb["early_core_tap_ps"],
               lib_max_clock_tree_path_ps={c: lib_ctp(d / f"{top}_{c}.lib") for c in ("tt", "ff")},
               contract="core tap insertion = die common latency + early_core_tap_ps (the kit's clk source latency "
                        "-early); lib max_clock_tree_path is information only (max over all internal flops)",
               files=files)
    (d / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    print(d, so.get("verdict"), "early", rb["early_core_tap_ps"], "lib ctp", man["lib_max_clock_tree_path_ps"])


if __name__ == "__main__":
    main()
