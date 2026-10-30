#!/usr/bin/env python3
"""DIE-S81-32/IQF fit check for the iqf__t1 ring_ff band form, on the iqf__t1 MAPPED netlist (S81-KITS-A kit
1_synth_odb.v, main plan_s13r2 band rects).

Reproduces landing_placement.tcl (main) for each band:
  before (band_ring=all): every ring cell FIRM, reserve ceil(w/0.4/site)*site x h -> ratio = reserve / band area.
  after  (ring_place=ff + OT_CLAND_FIT_RESERVE=1): only DFF|DHL|DLL|SDF cells FIRM; need = sum ceil(w/0.4/site)*site*h;
         sp = max(1, 0.90*band/need); each flop's reserved footprint fw = rw = ceil(w/0.4*sp/site)*site must be free of
         every other FIRM cell (tapcells: TAPCELL_ASAP7_75t_R 0.108 um, -distance 25 -> 50 um period per row, staggered 25
         um between rows; phase swept over 0..50 um in 0.54 um steps, worst phase reported) and of earlier ring flops;
         bit-major order (cland_ffkey), cursor fill: left to right, row by row from the band's low corner.
  fit = flops placed / flops (must be 1.0), rows used / rows in band.
usage: iqf_ringff_fit_1029.py PLAN NETLIST [OUT_JSON]
"""
import json, math, re, sys

SITE, RH, X0, Y0 = 0.054, 0.27, 4.32, 4.32          # asap7sc7p5t site, row height, CORE_AREA origin (config.mk)
TAPW, TAP_PERIOD, TAP_STAGGER = 0.108, 50.0, 25.0
LEF_W = {"DFFASRHQNx1": 1.404, "DFFHQNx1": 1.08, "DFFHQNx2": 1.134, "DFFHQNx3": 1.188, "DFFHQx4": 1.35,   # asap7sc7p5t_28_R_1x
         "DFFLQNx1": 1.08, "DFFLQNx2": 1.134, "DFFLQNx3": 1.188, "DFFLQx4": 1.35, "DHLx1": 0.81, "DHLx2": 0.864,
         "DHLx3": 0.918, "DLLx1": 0.81, "DLLx2": 0.864, "DLLx3": 0.918, "SDFHx1": 1.35, "SDFHx2": 1.404, "SDFHx3": 1.458,
         "SDFHx4": 1.674, "SDFLx1": 1.35, "SDFLx2": 1.404, "SDFLx3": 1.458, "SDFLx4": 1.674}   # single-row (0.27 um) masters
SEQ = re.compile(r"DFF|DHL|DLL|SDF")


def sites(x):
    return int(math.ceil(round(x / SITE, 6)))


def ffkey(nm):
    m = re.match(r"^([^\[]*)\[([0-9]+)\\?\]\\?\[([0-9]+)\\?\](.*)$", nm)
    if m:
        b, s, i, t = m.groups()
        return "%s|%09d|%09d|%s" % (b.rstrip("\\"), int(i), int(s), t)
    return nm


def cells(netlist, inst):
    pat = re.compile(r"^\s*(\w+)_ASAP7_75t_R\s+(\S+)")
    want = re.compile(r"(^|[/.\\])%s[/.]" % re.escape(inst))
    out = []
    for ln in open(netlist):
        m = pat.match(ln)
        if m and want.search(m.group(2)):
            out.append((m.group(1), m.group(2)))
    return out


def simulate(rect, ffs, sp, phase):
    ax, ay, bx, by = rect
    sx = X0 + math.ceil(round((ax - X0) / SITE, 6)) * SITE
    r0 = int(math.ceil(round((ay - Y0) / RH, 6))); r1 = int(math.floor(round((by - Y0) / RH, 6)))  # rows [r0, r1)
    rows = r1 - r0; r = r0; x = sx; placed = 0; used_rows = set()
    taps = {}
    for rr in range(r0, r1):
        off = phase + (TAP_STAGGER if rr % 2 else 0.0)
        k0 = math.floor((ax - X0 - off) / TAP_PERIOD) - 1
        taps[rr] = [X0 + off + k * TAP_PERIOD for k in range(k0, k0 + int((bx - ax) / TAP_PERIOD) + 4)]
    for w in ffs:
        rw = max(w, sites(w / 0.4 * sp) * SITE)
        while r < r1:
            ok = False
            while x + w <= bx + 1e-9:
                hit = [t for t in taps[r] if x < t + TAPW - 1e-9 and x + rw > t + 1e-9]
                if hit:
                    x = X0 + math.ceil(round((max(hit) + TAPW - X0) / SITE, 6)) * SITE
                    continue
                ok = True
                break
            if ok:
                break
            r += 1; x = sx
        if r >= r1:
            break
        placed += 1; used_rows.add(r); x = x + rw
    return placed, rows, len(used_rows)


def main():
    plan, netlist = sys.argv[1], sys.argv[2]
    P = json.load(open(plan)); t = P["partition_types"]["iqf__t1"]
    bands = t["clock"]["landing_contract"]["bands"]; res = {}
    for bus in sorted(bands):
        b = bands[bus]; rect = b["rect_um"]; area = (rect[2] - rect[0]) * (rect[3] - rect[1])
        cl = cells(netlist, b.get("instance", "u_cland_" + bus))
        unknown = sorted({m for m, _ in cl if SEQ.search(m) and m not in LEF_W})
        if unknown:
            raise SystemExit(f"no LEF width for {unknown}")
        ff = sorted(((ffkey(n), LEF_W[m]) for m, n in cl if SEQ.search(m)))
        ffs = [w for _, w in ff]
        need = sum(sites(w / 0.4) * SITE * RH for w in ffs)
        sp = max(1.0, 0.90 * area / need)
        worst = None
        for k in range(int(TAP_PERIOD / 0.54)):
            p = simulate(rect, ffs, sp, k * 0.54)
            if worst is None or (p[0], -p[2]) < (worst[0], -worst[2]):
                worst = p
        res[bus] = dict(rect_um=rect, band_um2=round(area, 1), ring_cells=len(cl), ring_flops=len(ffs),
                        ring_place=b.get("ring_place", "all"),
                        ff_need_um2=round(need, 1), ff_ratio=round(need / area, 3), ff_ratio_vs_0p9band=round(need / (0.9 * area), 3),
                        spread=round(sp, 4), worst_phase_flops_placed=worst[0], band_rows=worst[1], worst_phase_rows_used=worst[2],
                        fits=worst[0] == len(ffs))
        print(f"{bus}: band {area:.0f} um2, {len(cl)} ring cells, {len(ffs)} flops; ff need {need:.0f} um2 = {need/area:.2f} x band "
              f"({need/(0.9*area):.2f} x 0.9 band), spread {sp:.4f}; packing worst tap phase: {worst[0]}/{len(ffs)} flops in "
              f"{worst[2]}/{worst[1]} rows -> {'FITS' if worst[0]==len(ffs) else 'DOES NOT FIT'}")
    if len(sys.argv) > 3:
        json.dump(res, open(sys.argv[3], "w"), indent=1)


if __name__ == "__main__":
    main()
