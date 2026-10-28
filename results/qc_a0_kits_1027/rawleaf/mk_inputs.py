#!/usr/bin/env python3
"""QC-A0-KITS rawleaf re-kit inputs: pin contract LEF (M5 ceiling: Codex M6 E-face pins -> nearest free M4 track),
spec.json, mini plan + recipe + master-plan TRIAL slice with the 12.8a centre clock entry (57.672, 70.2)."""
import json, re, sys, hashlib, gzip
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])   # codex leaf_kit dir, repo-relative results dir (absolute path)
repo_rel = sys.argv[3]                           # results dir relative to repo root
out.mkdir(parents=True, exist_ok=True)
MOD = "ot_qwen_tile_lsl_rawfault_m3"
W, H = 115.344, 140.4
pins = json.load(open(src / "pins.json"))["pins"]
v = gzip.open(src / "rawleaf_keep.v.gz", "rt").read()
hdr = v[v.index("module " + MOD):]
dirs = {}
for m in re.finditer(r"^\s*(input|output)\s*(\[(\d+):(\d+)\])?\s*([A-Za-z_]\w*)\s*;", hdr[:20000], re.M):
    d, msb, lsb, n = m.group(1), m.group(3), m.group(4), m.group(5)
    if msb is None:
        dirs[n] = d.upper()
    else:
        for b in range(int(lsb), int(msb) + 1):
            dirs[f"{n}[{b}]"] = d.upper()
assert set(dirs) == {p["name"] for p in pins}, (len(dirs), len(pins))
RECT = {"M3": (0.018, 0.038), "M4": (0.084, 0.024), "M5": (0.024, 0.084)}
used = {(p["layer"], round(p["y"] if p["face"] in "EW" else p["x"], 4)) for p in pins if p["layer"] != "M6"}
moved, newp = [], []
for p in pins:
    q = dict(p)
    if p["layer"] == "M6":
        assert p["face"] == "E"
        k = round((p["y"] - 0.012) / 0.048)
        for dk in (0, 1, -1, 2, -2, 3, -3):
            y = round(0.012 + (k + dk) * 0.048, 4)
            if ("M4", y) not in used and all(abs(y - u[1]) >= 0.096 - 1e-6 for u in used if u[0] == "M4"):
                break
        else:
            raise SystemExit("no free M4 track for " + p["name"])
        used.add(("M4", y)); q.update(layer="M4", y=y); moved.append((p["name"], p["y"], y))
    if q["layer"] == "M5":   # N/S-face M5 pins onto the kit M5 track (x_offset 0.012, pitch 0.048)
        x = round(0.012 + round((q["x"] - 0.012) / 0.048) * 0.048, 4)
        if abs(x - q["x"]) > 1e-6:
            moved.append((q["name"] + "@x", q["x"], x)); q["x"] = x
    newp.append(q)
# min spacing check on each face/layer
for L in ("M4", "M5"):
    cs = sorted((q["y"] if q["face"] in "EW" else q["x"]) for q in newp if q["layer"] == L)
    gaps = [b - a for a, b in zip(cs, cs[1:])]
    print(L, len(cs), "min gap", round(min(gaps), 4) if gaps else None)
lef = [f"VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", f"MACRO {MOD}", "  CLASS BLOCK ;",
       "  ORIGIN 0 0 ;", f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y ;"]
for q in newp:
    pw, ph = RECT[q["layer"]]
    f = q["face"]
    if f == "E": x0, x1, y0, y1 = W - pw, W, q["y"] - ph / 2, q["y"] + ph / 2
    elif f == "W": x0, x1, y0, y1 = 0, pw, q["y"] - ph / 2, q["y"] + ph / 2
    elif f == "N": x0, x1, y0, y1 = q["x"] - pw / 2, q["x"] + pw / 2, H - ph, H
    else: x0, x1, y0, y1 = q["x"] - pw / 2, q["x"] + pw / 2, 0, ph
    lef += [f"  PIN {q['name']}", f"    DIRECTION {dirs[q['name']]} ;", "    USE " + ("CLOCK" if q["name"] == "clk" else "SIGNAL") + " ;",
            "    PORT", f"      LAYER {q['layer']} ;", f"        RECT {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;", "    END", f"  END {q['name']}"]
lef += ["  OBS", "    LAYER M1 ;", f"      RECT 0 0 {W} {H} ;", "    LAYER M2 ;", f"      RECT 0 0 {W} {H} ;",
        "    LAYER M3 ;", f"      RECT 0 0 {W} {H} ;", "    LAYER M4 ;", f"      RECT 0.5 0.5 {W-0.5} {H-0.5} ;",
        "    LAYER M5 ;", f"      RECT 0.5 0.5 {W-0.5} {H-0.5} ;", "  END", f"END {MOD}", "END LIBRARY"]
(out / "rawleaf_contract.lef").write_text("\n".join(lef) + "\n")
spec = dict(top=MOD, sources=[f"{repo_rel}/rtl/rawleaf_keep.v"], clock_port="clk", reset_ports=["rst_n"],
            route=dict(pd=0.6), note="Codex rawfault cut leaf (codex/qc-a0-2157@b7da9afaa leaf_kit/rawleaf_keep.v.gz, unchanged)")
(out / "spec.json").write_text(json.dumps(spec, indent=1) + "\n")
plan = dict(schema="opentallas.qc_a0_child_plan.v0", note="QC-A0-KITS child contract (R3 B_child), NOT the die plan",
            die=dict(name="qwen_compute", period_ps=833.0),
            clock=dict(insertion_ps=201.0, insertion_ff_ps=161.5, insertion_tol_ps=20.0),
            master_plan=dict(required=False, sha256="qc-a0-r3b-child-contract-unfrozen"),
            partition_types={"a0_rawleaf": dict(contents=[dict(module=MOD)])})
(out / "plan_child.json").write_text(json.dumps(plan, indent=1) + "\n")
rec = {MOD: dict(plan=f"{repo_rel}/plan_child.json", lef_contract=f"{repo_rel}/rawleaf_contract.lef", plan_type="a0_rawleaf",
                 ref_tile=repo_rel, suffix="a0k", insertion_ps=201.0, insertion_ff_ps=161.5,
                 insertion_basis="QC-CORES-2 R3 B_child 201 TT / 161.5 FF (child-only mean, UNCHECKED-model)",
                 util=0.6, insertion_balance=True)}
(out / "recipes.json").write_text(json.dumps(rec, indent=1) + "\n")
cx, cy = 57.660, 70.2   # R3 plan point 57.672 snapped to the M5 track (0.012 + 0.048k), -0.012 um
sl = dict(schema="opentallas.master_plan_slice.v1", kind="core", die="qwen_compute", type=MOD, module=MOD, core_clock_port="clk", pushdown=dict(form="centre clock entry only: the parent A0 island drives this child (QC-CORES-2 R2/R3); no in-child island cells"),
          master_plan_sha256="qc-a0-r3b-child-contract-unfrozen", frozen=False, outline_um=[W, H], instances=[],
          islands=[dict(name="E0_centre_entry", rect_um=[round(cx - 0.54, 4), round(cy - 0.54, 4), round(cx + 0.54, 4), round(cy + 0.54, 4)],
                        centre_um=[cx, cy], clock_pin=dict(layer="M5", xy_um=[cx, cy]))],
          keepouts=[], bays=[], entry_pins=[], hard_cores=[], gates={},
          note="QC-CORES-2 A0 R2/R3 child centre entry (12.8a); trial slice: A0 plan event not frozen")
(out / "slice").mkdir(exist_ok=True)
(out / "slice" / f"{MOD}.json").write_text(json.dumps(sl, indent=1) + "\n")
(out / "m6_to_m4_moves.json").write_text(json.dumps(dict(n=len(moved), moves=moved), indent=0) + "\n")
print("pins", len(newp), "moved M6->M4", len(moved), "max dy", max(abs(a - b) for _, a, b in moved))
