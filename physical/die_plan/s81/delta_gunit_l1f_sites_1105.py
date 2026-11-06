#!/usr/bin/env python3
"""S81 gunit__t1 l1f SRAM sites (DIE-S81-66/PLAN 11-05, COORD 19:37 (f), KW-RELAUNCH-1 row gunit__t1 @4 ORD-2013).

The four router front leaves dsdv_gunit_l1f (u_gunit.g_l1f[q].u_l1f, q = 0..3) stay soft in gunit__t1; each holds
2 x ot_sram_1r1w_128x256_m1_r2c2 (g_m[m].u_b, dsdv_gunit_l1f.sv:244).  No plan row declared these 8 macros, so synth
stopped ORD-2013 'LEF master ot_sram_1r1w_128x256_m1_r2c2 not found' (kit-wave attempt_4 1_synth.log:36; the 1_2_yosys.v
of that attempt lists exactly these 8 instances beside the 10 declared dsdv_gunit_l* cores).  The PROVISIONAL child
views were not the cause.  This event adds 8 static macro sites as contents[] rows in the form of
csite_1105/delta_c_macro_sites_1105.py (same column packer and keepouts: 8.64 lattice + per-master track offset,
>= 10.8 channels, clear of ft corridors, landing rects, hard cores +10.8, clock / reset / station points +21.6, 43.2
edge band), except that the columns are packed right to left from the stack leaf u_l1c / u_l1 (x 665.28) and centred
on their rows (y 380-596), so each l1f bias SRAM sits <= ~300 um from the L1 stack it serves (not at the far W edge).  No outline, bus, ft slot, hard core, clock tap, reset, neighbour or die datum changes.  A second run refuses.

usage: delta_gunit_l1f_sites_1105.py PLAN_IN PLAN_OUT
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "csite_1105"))
import delta_c_macro_sites_1105 as C  # noqa: E402

TYPE = "gunit__t1"
MASTER = "ot_sram_1r1w_128x256_m1_r2c2"
INSTS = {TYPE: {MASTER: [f"u_bound.u_u_gunit_g_l1f_{q}_u_l1f.g_m[{m}].u_b" for q in range(4) for m in range(2)]}}
C.TAG = "DIE-S81-66/PLAN 11-05 gunit l1f SRAM site (delta_gunit_l1f_sites_1105.py)"
C.RADIUS = {}
X_RIGHT = 665.28          # u_gunit.u_l1c origin x: columns end left of it (its +10.8 halo is a keepout anyway)
Y_CENTRE = 488.16         # middle of the u_l1 / u_l1c rows (380.16 .. 596.16)


def place(tn, t, insts, masters):
    """C.place, but columns right to left from X_RIGHT, rows filled outward from Y_CENTRE (nearest legal site first)."""
    W, H = t["outline_um"]
    rects, pts = C.keepouts(t)
    sites = []
    for mod in sorted(insts):
        q = sorted(insts[mod])
        (w, h), (dx, dy) = masters[mod]["size"], masters[mod]["off"]
        x = C.snap(X_RIGHT - w - dx - C.CH) - C.G
        while q:
            assert x >= C.EDGE, (tn, len(q), mod, "unplaced")
            ys = [C.snap(C.EDGE) + k * C.G for k in range(int((H - 2 * C.EDGE) / C.G) + 1)]
            ys = [y for y in ys if y + h + dy <= H - C.EDGE]
            ys.sort(key=lambda y: (abs(y + h / 2 - Y_CENTRE), y))
            col = []
            for y in ys:
                b = (x, y, x + w + dx, y + h + dy)
                if C.hit(b, rects, pts) or any(y < cy + h + dy + C.CH and cy < y + h + dy + C.CH for cy in col):
                    continue
                col.append(y)
                if len(col) == len(q):
                    break
            for y in sorted(col):
                sites.append(dict(inst=q.pop(0), module=mod, status="new", lef=masters[mod]["lef"], lib=masters[mod]["lib"],
                                  origin_um=[round(x + dx, 3), round(y + dy, 3)], outline_um=[w, h], orient="R0",
                                  obs_max="M4", note=C.TAG))
            x = C.snap(x - w - dx - C.CH) - C.G if col else round(x - C.G, 4)
    return sites


C.place = place


def main():
    src, dst = sys.argv[1:3]
    t = json.load(open(src))["partition_types"][TYPE]
    have = {c["inst"] for c in t.get("contents", []) + t.get("hard_cores", [])}
    assert not have & set(INSTS[TYPE][MASTER]), "second run"
    assert sum(c["module"] == "dsdv_gunit_l1f" for c in t.get("hard_cores", [])) == 0, "l1f is a hard core now"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(INSTS, f)
    sys.argv = [sys.argv[0], src, dst, f.name]
    C.main()
    Path(f.name).unlink()


if __name__ == "__main__":
    main()
