#!/usr/bin/env python3
"""Collect DH54-PAD coupon results into one JSON. argv: OUT_DIR RESULT_JSON"""
import glob, json, os, re, sys

out, dst = sys.argv[1], sys.argv[2]
RUNS = {"m0_kit": "mode0 baseline + kit ot_keep_regs hook (negative control)",
        "m1_nohook": "mode1 wire keep/dont_touch, no canonicalize hook",
        "m1_kit": "mode1 wire keep/dont_touch + kit ot_keep_regs hook (kit default path)",
        "m0_cellkeep": "mode0 + cell_keep_hook_1102.tcl (packet per-bit cell KEEP recipe, selector fixed for pinned frontend)",
        "m2_kit": "mode2 kept generic leaf (keep_hierarchy) + kit hook",
        "m3_kit": "mode3 explicit 14 native DFFHQNx1 leaf + kit hook"}


def stat(run):
    p = f"{out}/{run}/flow/reports/asap7/{run}/base/synth_stat.txt"
    txt = open(p).read()
    top = txt.split("=== head_pad_fragment ===")[1] if "=== head_pad_fragment ===" in txt else txt
    cells, ncells = {}, None
    for l in top.splitlines():
        m = re.match(r"^\s+(\d+)\s+([\d.\-]+)\s+\d+\s+[\d.\-]+\s+(\S+)$", l)
        if m and m.group(3).endswith("_ASAP7_75t_R"):
            cells[m.group(3)] = {"n": int(m.group(1)), "area_um2": float(m.group(2))}
        m = re.match(r"^\s+(\d+)\s+[\d.\-]+\s+\d+\s+[\d.\-]+\s+cells$", l)
        if m:
            ncells = int(m.group(1))
    area = [float(x) for x in re.findall(r"Chip area for (?:top )?module '\\head_pad_fragment': ([\d.]+)", txt)]
    return {"cells_total": ncells, "chip_area_um2": area[-1] if area else None,
            "dff": sum(v["n"] for k, v in cells.items() if k.startswith("DFF")), "cells": cells}


def canon(run):
    p = f"{out}/{run}/flow/results/asap7/{run}/base/1_1_yosys_canonicalize.rtlil"
    t = open(p).read()
    return {"canon_dff_cells": len(re.findall(r"^\s*cell \$(?:_?dff|_DFF_P_)\S*", t, re.M)),
            "canon_keep_attr_on_cells": len(re.findall(r"attribute \\keep 1\s*\n\s*cell \$_?(?:dff|DFF)", t))}


def odb(run):
    p = f"{out}/{run}/odb_count.txt"
    c = {}
    if os.path.exists(p):
        for l in open(p):
            _, m, n = l.split()
            c[m] = int(n)
    return {"odb_insts": sum(c.values()) if c else None, "odb_dff": sum(v for k, v in c.items() if k.startswith("DFF")) if c else None}


res = {"image_id": open(f"{out}/image_id.txt").read().strip(), "versions": open(f"{out}/versions.txt").read(),
       "synth_runs": {}, "rtl_controls": {}}
for run, desc in RUNS.items():
    if not os.path.isdir(f"{out}/{run}"):
        continue
    r = {"desc": desc, **stat(run), **canon(run), **odb(run)}
    f = json.load(open(f"{out}/formal/{run}.formal.json"))
    r["formal"] = {k: f.get(k) for k in ("dut_ff_total", "dut_hold_ff", "dut_out_ff", "dut_ff_inits",
                                          "bijection_structural", "idle_fold", "step", "step_passing_maps",
                                          "verdict", "structural_error", "classify_issues")}
    r["hold_bits_surviving"] = f.get("dut_hold_ff")
    for diag, tagw in (("fold_trace", "FOLDTRACE"), ("optdff_probe", "OPTDFF_PROBE")):
        p = f"{out}/{run}/{diag}.log"
        if os.path.exists(p):
            seq, cur = [], None
            for l in open(p, errors="replace"):
                l = l.strip()
                if l.startswith(tagw):
                    cur = l.split()[1]
                elif cur and l.endswith(" objects."):
                    seq.append((cur, int(l.split()[0])))
                    cur = None
            r[diag] = seq
    res["synth_runs"][run] = r
base = res["synth_runs"].get("m0_kit")
if base:
    for run, r in res["synth_runs"].items():
        r["delta_vs_m0_kit"] = {"ff": r["dff"] - base["dff"], "cells": r["cells_total"] - base["cells_total"],
                                "area_um2": round(r["chip_area_um2"] - base["chip_area_um2"], 6)}
for p in sorted(glob.glob(f"{out}/formal/rtl_*.formal.json")):
    f = json.load(open(p))
    res["rtl_controls"][f["tag"]] = {k: f.get(k) for k in ("dut_ff_total", "dut_hold_ff", "dut_ff_inits",
                                                         "bijection_structural", "idle_fold", "step", "verdict",
                                                         "structural_error")}
st = f"{out}/m0_cellkeep_pkt.status"
if os.path.exists(st):
    lines = open(st).read().splitlines()
    res["packet_cell_keep_hook_as_shipped"] = {"status": lines[-1] if lines else None,
                                               "evidence": [l for l in lines if "Assertion" in l or "ERROR" in l][:3]}
json.dump(res, open(dst, "w"), indent=1)
for run, r in res["synth_runs"].items():
    print(f"{run:12s} dff={r['dff']:3d} hold={r['hold_bits_surviving']} cells={r['cells_total']} area={r['chip_area_um2']}"
          f" d={r.get('delta_vs_m0_kit')} verdict={r['formal']['verdict']} idle={r['formal']['idle_fold']}")
for t, r in res["rtl_controls"].items():
    print(f"{t:14s} verdict={r['verdict']} step={r.get('step')} inits={r.get('dut_ff_inits')} idle={r.get('idle_fold')}")
