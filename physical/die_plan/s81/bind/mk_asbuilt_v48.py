#!/usr/bin/env python3
"""ELEM-S81 bind48 10-24: the S81 as-built binding section for plan v4.8 (ea36999b), rebuilt from BINDER4-S81's
asbuilt_s81_r8.json (v4.6 record, 474d1c07a2) after its run dir was lost with the old scratch.
Paths change (and land_r8 / note; + the repo ot_reset_sync.sv preferred, below): cap30 inputs = the recovered cap30 gen-main receipt
(intel2:/srv/opentallas-scratch/claude/recovered-1023/stw-s81c-cap30/gen-main: bind/bind = RUN/cap30/bind/bind (copy),
src = RUN/cap30/src_gm), the p9src / binder4 worktree files = this repo worktree (main, plan v4.8 frame band kits).
Usage: mk_asbuilt_v48.py RUN WT {off|r8} OUT.json"""
import json
import sys

run, wt, mode, out = sys.argv[1:5]
src = json.load(open(f"{wt}/physical/die_plan/s81/bind/asbuilt_s81_r8.json"))
OLD = "/home/ubuntu/scratch/binder4-1023/s81"


def fix(s):
    if not isinstance(s, str):
        return s
    s = s.replace(f"{OLD}/p9src", wt).replace("/home/ubuntu/wt/binder4-s81-1023", wt)
    s = s.replace(f"{OLD}/r8v3/s81_r8_landing.json", f"{run}/r8/s81_r8_landing_v48.json")
    return s.replace(OLD, run)


def walk(x):
    if isinstance(x, dict):
        return {k: walk(v) for k, v in x.items()}
    if isinstance(x, list):
        return [walk(v) for v in x]
    return fix(x)


ab = walk(src)
# kit-rtl adds the repo's rtl/lib/ot_reset_sync.sv (the partition reset synchroniser) to every kit and refuses two
# different files of one basename; the cap30 snapshot's copy predates OUTPUT_COPIES/TREE (defaults = the old body, no
# as-built instance sets them), so the repo copy is preferred for the as-built leaves too (one definition per kit).
rs = f"{wt}/rtl/lib/ot_reset_sync.sv"
ab["files"].append(rs)
ab["prefer"].append(rs)
ab["note"] = ("ELEM-S81 bind48 10-24: " + src["note"].replace("Plan v4.6 claude/s81-p9-1023 @5be68388d (sha 58b8a4cc).",
              "Plan v4.8 main 847f8568f3 (sha ea36999b).") + " Paths rebuilt by bind/mk_asbuilt_v48.py (" + mode + ").")
if mode == "off":
    for k in ("land_align", "land_r8", "land_r8_exempt", "land_r8_note"):
        ab.pop(k, None)
else:
    ab["land_r8_note"] = ("ELEM-S81 bind48: r8 table = r8.py pads --replica type --bus leaf --exempt fault --landed "
                          "'^(x|xo)_[WE][0-5]_' --landed '^xring__' --landed '^sid_s_' (S81-P9-R8EQ v4.8 LANDED BUNDLES rule, "
                          "r8eq_v48_checks.json) on bus_groups of the land_align-off bind of plan v4.8")
json.dump(ab, open(out, "w"), indent=1)
