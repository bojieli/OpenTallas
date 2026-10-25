#!/usr/bin/env python3
"""PATH-HBM/TKMCOND (GEOM-REVIEW PASS-COND 15:24 [PATH-HBM-TKMCLKBUF] conditions (2) and (3), 2026-10-25).

    python3 path_hbm_tkm_cond.py --src <plan dir> --out <new plan dir>

(2) Leg slew.  OpenROAD/OpenSTA probe (epyc1 path-hbm/tkmclk_cond, ASAP7 RVT TT/FF, flow RCX M6 RC, 80 ps in,
    BUFx4 load): an unrepeated BUFx12f leg ends at 206.3/195.5 ps (L4, 315.36 um) and 98.4/89.7 ps (L150, 203.04 um),
    over the ~80 ps limit.  Fix = SYMMETRIC repeaters, the same count on both legs of a buffer (GEOM rule, never an
    asymmetric fix): L4 2 x BUFx12f per leg (105.12-um segments: 45.9/39.8 ps), L150 1 per leg (101.52 um: 44.1/38.1 ps).
    Each repeater sits at its even split point of the leg, legalized on the site grid (0.054 x 0.27, R0), in the
    8.64-um inter-column clock-spine gap beside the leg (or the corridor), clear of every hard core and >= 2 um from
    every FT bit site / station.  Recorded as clock.branch_buffers[].leg_repeaters (check.py verifies symmetry, sites,
    segments <= 405).  Leg delays stay equal by construction (pair mismatch 0).
(3) tile31 <-> root pair.  The only root<->tile31 net is the 1-bit conv root -> tile31 (TOKEN CB21; it returns down
    the chain to tile0, whose up_out is already audited).  Its B2p_r1 chain (2 stations, 331.2-um hops) leaves the last
    station 812.8 um (clock-tap distance) from tile31's E-mid clock pin, > 400.  Re-stationed with 3 stations so every
    hop <= 360 um and every launch/capture tap pair <= 400 um: +1 conv cycle -> TOKEN schedule (reported).
    The reversed B2o entry 'u_tkm_SW_tile31.tile_conv|u_tkm_SW_root' (tile_conv is a tile INPUT; 5 stations into the
    root NE corner) is a stale leftover and is removed.
"""
import argparse, copy, json, os, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
import path_hbm_b2p as PB  # noqa: E402

SITE_X, SITE_Y = 0.054, 0.27
CELL = "BUFx12f_ASAP7_75t_R"
CELL_WH = (1.404, 0.27)
NREP = {"L4": 2, "L150": 1}
PROBE = {"L4": dict(unrepeated_end_slew_ps=dict(TT=206.3, FF=195.5), repeated_worst_slew_ps=dict(TT=45.9, FF=39.8),
                    delay_ps=dict(TT=121.5, FF=95.6)),
         "L150": dict(unrepeated_end_slew_ps=dict(TT=98.4, FF=89.7), repeated_worst_slew_ps=dict(TT=44.1, FF=38.1),
                      delay_ps=dict(TT=84.3, FF=65.4))}
CONV = "u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv|u_tkm_SW_tile31"
STALE = "u_tkm_SW_tile31.tile_conv|u_tkm_SW_root"
CONV_REGS = [[548.0, 1360.8], [908.0, 1360.8], [1268.0, 1360.8]]
TAP_MAX = 400.0


def snap(v, g):
    return round(round(v / g) * g, 4)


def apply(plan):
    t = plan["partition_types"]["root"]
    ck = t["clock"]
    taps = {tp["name"]: tp for tp in ck["taps"]}
    boxes = [(h["inst"], h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
              h["origin_um"][1] + h["outline_um"][1]) for h in t["hard_cores"]]
    rep = dict(repeaters=[], conv={}, probe=PROBE)

    def clear(ll):
        x0, y0 = ll
        x1, y1 = x0 + CELL_WH[0], y0 + CELL_WH[1]
        if any(x0 < bx1 and x1 > bx0 and y0 < by1 and y1 > by0 for _, bx0, by0, bx1, by1 in boxes):
            return False
        c = (x0 + CELL_WH[0] / 2, y0 + CELL_WH[1] / 2)
        return CK._buf_near_station(t, list(ll)) is None and CK._buf_near_station(t, list(c)) is None

    for b in ck["branch_buffers"]:
        corr = "L4" if "_L4_" in b["name"] else "L150"
        n = NREP[corr]
        q = b["xy"]
        reps = []
        for d in b["drives"]:
            tp = taps[d]["xy"]
            for k in range(1, n + 1):
                f = k / (n + 1)
                px, py = q[0] + (tp[0] - q[0]) * f, q[1] + (tp[1] - q[1]) * f
                # legal LL centred in the 8.64-um clock-spine gap E of the pin (4.32 um off the leg), else stepping E/W
                ll = None
                for dx in [4.32, 2.7, 5.94, 0.0, 7.56, -1.8, 9.18, 10.8, 12.6, 14.4, -3.6, -5.4]:
                    cand = (snap(px - CELL_WH[0] / 2 + dx, SITE_X), snap(py, SITE_Y))
                    if clear(cand):
                        ll = cand
                        break
                if ll is None:
                    raise ValueError(f"{b['name']} leg {d} rep {k}: no legal site near ({px:.2f},{py:.2f})")
                xy = [round(ll[0] + CELL_WH[0] / 2, 3), round(py, 3)]
                reps.append(dict(name=f"{b['name']}_r{d.rsplit('tile', 1)[1]}_{k}", tap=d, k=k, cell=CELL, xy=xy,
                                 cell_ll_um=[ll[0], ll[1]], cell_wh_um=list(CELL_WH), orient="R0"))
        b["leg_repeaters"] = reps
        b["leg_slew_probe"] = dict(corridor=corr, repeaters_per_leg=n, **PROBE[corr],
                                   pair_mismatch_ps=0.0, src="epyc1 path-hbm/tkmclk_cond/tkmclk_cond_report.json")
        b["note"] = b.get("note", "") + (f" | PATH-HBM TKMCOND: {n} symmetric BUFx12f repeater(s) per leg "
                                         f"(GEOM 15:24 cond 2, probe slew {PROBE[corr]['repeated_worst_slew_ps']})")
        rep["repeaters"] += [dict(buffer=b["name"], **{k: r[k] for k in ("name", "tap", "xy", "cell_ll_um")})
                             for r in reps]
    # (3) conv chain
    ist = t["internal_stations"]
    st = [e for e in ist if e.get("conn") == STALE]
    t["internal_stations"] = ist = [e for e in ist if e.get("conn") != STALE]
    rep["conv"]["stale_removed"] = [dict(conn=e["conn"], regs=len(e["regs_um"])) for e in st]
    e = next(e for e in ist if e.get("conn") == CONV)
    old = list(e["regs_um"])
    e["regs_um"] = [list(p) for p in CONV_REGS]
    for p in e["regs_um"]:
        if any(x0 < p[0] < x1 and y0 < p[1] < y1 for _, x0, y0, x1, y1 in boxes):
            raise ValueError(f"conv station {p} inside a hard core")
    pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
    hops = [round(abs(a[0] - b_[0]) + abs(a[1] - b_[1]), 2) for a, b_ in zip(pts, pts[1:])]
    assert max(hops) <= 360.0 + 1e-6, hops
    tr, t31 = taps["u_tkm_SW_root"]["xy"], taps["u_tkm_SW_tile31"]["xy"]
    tpts = [tr] + e["regs_um"] + [t31]
    tapd = [round(abs(a[0] - b_[0]) + abs(a[1] - b_[1]), 2) for a, b_ in zip(tpts, tpts[1:])]
    assert max(tapd) <= TAP_MAX + 1e-6, tapd
    e["note"] = (e.get("note", "") + f" | PATH-HBM TKMCOND (GEOM 15:24 cond 3): 3 stations, data hops {hops}, "
                 f"clock-tap distance per hop {tapd} (<= {TAP_MAX:g}); +1 conv cycle (TOKEN CB21 schedule)")
    rep["conv"].update(old_regs=old, new_regs=e["regs_um"], data_hops_um=hops, tap_dist_um=tapd, cycle_delta=+1)
    return rep


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--src", required=True)
    a.add_argument("--out", required=True)
    x = a.parse_args()
    src, out = Path(x.src), Path(x.out)
    if out.exists():
        raise ValueError("new output directory required")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith(("g0", "gates", "netcut")) or p.name == "die_plan.json" or p.suffix in (".log", ".exit"):
            continue
        if p.is_symlink():
            os.symlink(os.readlink(p), out / p.name)
        elif p.is_dir():
            shutil.copytree(p, out / p.name, symlinks=True)
        else:
            shutil.copy2(p, out / p.name)
    plan = json.loads((src / "die_plan.json").read_text())
    rep = apply(plan)
    plan["note"] = plan.get("note", "") + " | PATH-HBM TKMCOND: symmetric TKM clock leg repeaters + conv 3-station chain"
    S.Plan(plan, out / "die_plan.json")
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    rep.update(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), out_plan_sha256=PB.sha(out / "die_plan.json"))
    (out / "tkm_cond_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep["conv"], indent=1))
    for r in rep["repeaters"]:
        print(r)


if __name__ == "__main__":
    main()
