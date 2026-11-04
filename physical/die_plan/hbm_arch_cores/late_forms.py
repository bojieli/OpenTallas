#!/usr/bin/env python3
"""Late-stage forms for HBM kits that stopped or spin before sign-off (DIE-HBM-62/FLOW); only sign-off blocks (OWNER 11-03).

grt KIT [--from-failed]  class GRT-NEAR-MISS: GRT stopped on a small congestion overflow.  Every global_route may finish
    with congestion, including the -end_incremental route after hold repair (it does not read GLOBAL_ROUTE_ARGS); detail
    route clears it or DRC at sign-off decides.  Recipe as DIE-QC-66 NL v2.  --from-failed starts GRT from the
    hold-repaired 5_1_grt-failed.odb (as 4_cts.odb; old one kept as 4_cts.prehold.odb), so hold repair is not repeated.
    Not for overflow in the thousands: that core needs a re-form.
gpl KIT  class GPL-SPIN: routability-driven global placement of a macro die runs out of filler and its overflow stays
    near 0.33-0.40 for >10k Nesterov iterations (idx_topk_link, idx_selector_sel, pdie_serdes: > 9 h).  3_3 runs without
    -routability_driven; GRT and sign-off still judge routing.
Then: run_kit_hbm.sh KIT finish (resumes at the first unfinished stage).
"""
import argparse
import re
import shutil
from pathlib import Path

GRT = """# DIE-HBM-62/FLOW class GRT-NEAR-MISS: every global_route may finish with congestion; sign-off judges the routed result.
if {[info commands ot_gr_strict] eq ""} {
  rename global_route ot_gr_strict
  proc global_route {args} {
    if {[lsearch -exact $args -start_incremental] < 0 && [lsearch -exact $args -allow_congestion] < 0} {
      lappend args -allow_congestion
    }
    uplevel 1 [list ot_gr_strict {*}$args]
  }
}
"""
GPL = """# DIE-HBM-62/FLOW class GPL-SPIN: no routability loop in 3_3; GRT and sign-off judge routing.
if {[info commands ot_gp_full] eq ""} {
  rename global_placement ot_gp_full
  proc global_placement {args} {
    set i [lsearch -exact $args -routability_driven]
    if {$i >= 0} {set args [lreplace $args $i $i]}
    uplevel 1 [list ot_gp_full {*}$args]
  }
}
"""


def hook(kit, stage, name, text):
    """Write KIT/name and source it first from the kit's PRE_<stage>_TCL script."""
    kit = Path(kit)
    m = re.search(rf"^(?:override )?export PRE_{stage}_TCL = /work/(\S+)", (kit / "config.mk").read_text(), re.M)
    if not m:
        raise SystemExit(f"{kit}: no PRE_{stage}_TCL script in config.mk")
    (kit / name).write_text(text)
    pre = kit / m[1]
    src = f"source /work/{name}\n"
    if src not in pre.read_text():
        pre.write_text(src + pre.read_text())


def from_failed(kit):
    base = next(Path(kit).glob("run/results/asap7/*/base"))
    failed, cts = base / "5_1_grt-failed.odb", base / "4_cts.odb"
    if not failed.is_file():
        raise SystemExit(f"{kit}: no 5_1_grt-failed.odb")
    if not (base / "4_cts.prehold.odb").exists():
        shutil.copy2(cts, base / "4_cts.prehold.odb")
    shutil.copy(failed, cts)
    failed.unlink()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("form", choices=["grt", "gpl"])
    ap.add_argument("kit")
    ap.add_argument("--from-failed", action="store_true")
    a = ap.parse_args()
    if a.form == "grt":
        hook(a.kit, "GLOBAL_ROUTE", "grt_near_miss.tcl", GRT)
        if a.from_failed:
            from_failed(a.kit)
    else:
        hook(a.kit, "GLOBAL_PLACE", "gpl_no_routability.tcl", GPL)
    print("LATE_FORM", a.form, a.kit)
