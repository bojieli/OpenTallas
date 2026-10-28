#!/usr/bin/env python3
"""QC-PG-4: mixed-pitch bump field for a QC-PG-MAP window kit. Copies a kit dir, rewrites psm/bumps.tcl:
fine field (pattern FINE) where the bump centre lies inside an A0 core outline (loads_A.json, die coords),
base 150-um / 70-um-pad field (the kit's own bumps) where it does not.
usage: mixbump.py SRC_KIT DST_KIT loads_A.json WX0 WY0 FINE   FINE = p75 | p2x | none(base only, check)"""
import json, re, shutil, sys
from pathlib import Path
src, dst, la, wx0, wy0, fine = sys.argv[1], Path(sys.argv[2]), sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
DIL = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0   # fine field = A0 outlines dilated by DIL um (DIL 80 covers the ~147-um streets)
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(src, dst, ignore=shutil.ignore_patterns("ir_*.csv", "psm.log", "psm_*.rpt"))
A = [[r[0]-wx0-DIL, r[1]-wy0-DIL, r[2]-wx0+DIL, r[3]-wy0+DIL] for r, d in json.load(open(la))]
inA = lambda x, y: any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in A)
bt = (dst / "psm/bumps.tcl").read_text()
head, rest = bt.split("\not_pad ", 1)
base = re.findall(r"^ot_pad (VDD|VSS) \d+ (\S+) (\S+)$", bt, re.M)
W = 2972.16
pads = []
KEEP = len(sys.argv) > 8 and sys.argv[8].startswith("keep")   # keepNN: keep every coarse bump >= NN um (Chebyshev) from all fine bumps
KD = float(sys.argv[8][4:] or 55) if KEEP else 0
coarse = [(n, float(x), float(y)) for n, x, y in base]
if not KEEP:
    for n, x, y in coarse:
        if fine == "none" or not inA(x, y): pads.append((n, x, y, 70))
if fine != "none":
    sx, sy = (75.0, 75.0) if fine == "p75" else (75.0, 150.0)
    i = 0; x = 18.66
    while x < W:
        j = 0; y = 66.3 if fine == "p75" else 76.8
        while y < W:
            if inA(x, y): pads.append(("VDD" if (i + j) % 2 == 0 else "VSS", round(x, 2), round(y, 2), 37.5))
            j += 1; y += sy
        i += 1; x += sx
if KEEP:
    fp = [(x, y) for _, x, y, _ in pads]
    for n, x, y in coarse:
        if all(max(abs(x - a), abs(y - b)) >= KD for a, b in fp): pads.append((n, x, y, 70))
head = head.replace("proc ot_pad {net k bx by} {\n  global block m9 bump_dbu bump_shapes pad_pins pad_fallback pad_area pad_half",
                    "proc ot_pad {net k bx by {pum 70}} {\n  global block m9 bump_dbu bump_shapes pad_pins pad_fallback pad_area\n  set pad_half [expr {round($pum*$bump_dbu/2.0)}]")
assert "pum" in head
out = [head] + [f"ot_pad {n} {k} {x} {y} {p}" for k, (n, x, y, p) in enumerate(pads)]
nv = sum(1 for p in pads if p[0] == "VDD"); nf = sum(1 for p in pads if p[3] != 70)
out.append(f'puts "OT_BUMPS mixed {fine} bumps {len(pads)} vdd {nv} fine {nf} pad_pins $pad_pins pad_fallback $pad_fallback m9_contact_um2 [format %.1f $pad_area]"')
(dst / "psm/bumps.tcl").write_text("\n".join(out) + "\n")
m = json.loads((dst / "irwin.json").read_text()); m.update(dil_um=DIL, window=dst.name, bumps=len(pads), bumps_vdd=nv, bumps_fine=nf, fine=fine)
(dst / "irwin.json").write_text(json.dumps(m, indent=1) + "\n")
print(dst.name, "bumps", len(pads), "vdd", nv, "fine", nf, "base_kept", len(pads) - nf, "of", len(base))
