#!/usr/bin/env python3
"""HBM-FACE 10-25: census of shelled HBM core kits -> committed tables.

    face_shell_census.py --kits KITS_DIR --guards GUARDS_DIR [--gen-rc RC.txt] [--before B2L_GUARDS_DIR] --out RESULTS_DIR

KITS_DIR/<kit>/face_shell.json + freeze.json (gen_core_kit_hbm --face-shell on), GUARDS_DIR/<kit>/face_guard.json (synth
on the fleet: run_kit_hbm.sh synth).  Writes RESULTS_DIR/core_face_shell_latency.json (per module: +1 in / +1 out, drops),
core_face_shell_drops.json (plan change: unread input pins dropped per module and per pins table) and
core_face_shell_census.json (per view: generation, face_guard verdict before/after).
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import face_shell as FS


def bus_ranges(bits):
    by = defaultdict(list)
    for b in bits:
        m = re.match(r"^(.*)\[(\d+)\]$", b)
        if m:
            by[m[1]].append(int(m[2]))
        else:
            by[b] = None
    out = {}
    for n, ix in sorted(by.items()):
        out[n] = "scalar" if ix is None else (f"[{max(ix)}:{min(ix)}]" if len(ix) == max(ix) - min(ix) + 1 else sorted(ix))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kits", required=True)
    ap.add_argument("--guards", required=True)
    ap.add_argument("--gen-rc", default=None)
    ap.add_argument("--before", default=None, help="dir of <kit>/face_guard.json of the unshelled kits (before)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    kits = sorted(p for p in Path(a.kits).iterdir() if (p / "face_shell.json").is_file())
    reps = [k / "face_shell.json" for k in kits]
    FS.latency_table(out / "core_face_shell_latency.json", reps)
    gen = {}
    if a.gen_rc:
        for ln in Path(a.gen_rc).read_text().splitlines():
            v, rc = ln.rsplit(" ", 1)
            gen[v] = int(rc)
    drops, views = {}, []
    before = defaultdict(list)
    if a.before:
        for f in Path(a.before).glob("*/face_guard.json"):
            r = json.loads(f.read_text())
            before[r.get("top")].append(dict(kit=f.parent.name, verdict=r["verdict"], fails=r.get("fail_counts")))
    for k in kits:
        J = json.loads((k / "face_shell.json").read_text())
        fz = json.loads((k / "freeze.json").read_text())
        m = J["module"]
        d = drops.setdefault(m, dict(dropped=bus_ranges(J["dropped"]), dropped_bits=len(J["dropped"]),
                                     unread_kept=bus_ranges(J["unread_kept"]), const_out_bits=J["const_out_bits"],
                                     const_out={n: len(c) for n, c in J["const_out"].items()},
                                     dup_out_bits=J["dup_out_bits"], feedthrough_bits=J["feedthrough_bits"],
                                     pins_files=[]))
        d["pins_files"].append(fz["pins_file"])
        if bus_ranges(J["dropped"]) != d["dropped"]:
            d.setdefault("conflict", []).append(fz["view"])
        g = Path(a.guards) / k.name / "face_guard.json"
        fg = json.loads(g.read_text()) if g.is_file() else None
        views.append(dict(view=fz["view"], module=m, kit=k.name, pins_plan=fz["face_shell"]["plan_pins"],
                          pins_kit=fz["pins"], dropped=len(J["dropped"]), face_flops=J["face_flops"],
                          face_guard=(fg["verdict"] if fg else "NOT RUN"),
                          face_guard_fails=(fg.get("fail_counts") if fg else None),
                          face_guard_checked=(fg.get("checked") if fg else None),
                          before=before.get(m, [])))
    kv = {v["view"] for v in views}
    for v, rc in gen.items():
        if v not in kv:
            views.append(dict(view=v, module=v.split("@")[0], kit=None, face_guard="NO KIT", gen_rc=rc))
    cnt = Counter(v["face_guard"] for v in views)
    bcnt = Counter(b["verdict"] for v in views for b in v.get("before", [])[:1])
    T = dict(schema="opentallas.hbm_arch.core_face_shell_census.v1",
             plan="physical/die_plan/hbm_arch/B2n (views_b2n.json, 280 views)",
             after=dict(cnt), before_same_modules_b2l=dict(bcnt), views=views)
    (out / "core_face_shell_census.json").write_text(json.dumps(T, indent=1) + "\n")
    D = dict(schema="opentallas.hbm_arch.core_face_shell_drops.v1",
             rule=("PLAN CHANGE (HBM-FACE): input pin bits the core never reads (yosys proc/flatten/opt, bench-checked) "
                   "are removed from the core pin table when the removal keeps pin names (top bits of a bus or the "
                   "whole bus); interior unread bits stay pins (unread_kept, registered).  Partition side: the driving "
                   "partition output for a dropped pin has no load (drop it from the partition table too)."),
             modules=dict(sorted(drops.items())),
             total_dropped_bits=sum(d["dropped_bits"] for d in drops.values()))
    (out / "core_face_shell_drops.json").write_text(json.dumps(D, indent=1) + "\n")
    print(f"census: {len(views)} views, face_guard after {dict(cnt)}; before (B2l, same modules) {dict(bcnt)}; "
          f"{len(drops)} modules, {D['total_dropped_bits']} dropped bits")


if __name__ == "__main__":
    main()
