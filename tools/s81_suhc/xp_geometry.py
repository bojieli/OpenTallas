#!/usr/bin/env python3
"""S81 HC POST express: stage counts and cut widths from the v13 geometry (stream s81hc-express-1013).

Mirrors the stage functions of rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_xp.sv (ot_s81_hc_xcol) and dsfd_sp_hc XP=1, so
the RTL's `+HC_XGEOM` printout can be checked against it, and states for every express run its Manhattan length, its
registered stage count and the longest stage (<= 500 um by construction: stages = ceil(length / reach)).

v13 numbers (el1013-s81hc.log 03:20 PT, post_express_spec.json conditional contract 9d693102...): half-cth slot
576.72 x 740.88 um, 10 head slots + 1,512 um corridor (y 12,571.2 .. 14,083.2) + 12 / 10 tail slots, field x
17,312.4 .. 19,128.96 (3 columns: pitch 619.92), column roots 840 um (crooty 200 + crootr 640) above the head.

    python3 tools/s81_suhc/xp_geometry.py [--ng 256] [--log sim.log] [--out geometry.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

G = dict(slot_h=74088, col_p=61992, corr=151200, root_h=84000, reach=50000)   # 0.01 um
GS, NCOL = 8, 3


def stg(d):
    return 1 if d <= G["reach"] else -(-d // G["reach"])


def plan(ng=256, head_rows=10, d=5120):
    ns = ng // GS
    np_ = (ns + NCOL - 1) // NCOL
    l1 = max(ns - 2 * np_, 0)
    ymid = head_rows * G["slot_h"] + G["corr"] // 2
    nt = -(-(ymid + G["root_h"]) // G["reach"])
    cols, runs = [], []

    def run(name, length, stages, bits):
        runs.append(dict(run=name, length_um=length / 100, stages=stages, max_stage_um=round(length / 100 / stages, 2),
                         bits=bits))

    run("mid->sequencer (command)", ymid + G["root_h"], nt, 85)
    run("sequencer->mid (done)", ymid + G["root_h"], nt, 9)
    run("mid->slab face (credit, fault, online)", ymid + G["root_h"], nt, 3)
    for c in range(NCOL):
        lc = (l1 if c == 1 else np_) * 2
        nh = min(lc, head_rows)
        ntl = lc - nh
        nrh, nrt = (nh + 2) // 3, (ntl + 2) // 3
        dx = 0 if c == NCOL // 2 else G["col_p"] * abs(c - NCOL // 2)

        def rsz(r):
            if r < nrh:
                return nh // nrh + (1 if r < nh % nrh else 0)
            t = r - nrh
            return ntl // nrt + (1 if t < ntl % nrt else 0)

        def rfi(r):
            return sum(rsz(q) for q in range(r))

        def yrow(i):
            return i * G["slot_h"] if i < nh else nh * G["slot_h"] + G["corr"] + (i - nh) * G["slot_h"]

        regs = []
        for r in range(nrh + nrt):
            f, z = rfi(r), rsz(r)
            yst = yrow(f)
            yco = yrow(f + z - 1) + G["slot_h"] if r < nrh else yrow(f)
            row = dict(region=r, first=f, size=z, y_words=4 * z, y_bits=128 * z,
                       go_station=stg(abs(yst - ymid) + dx), go_collector=stg(abs(yco - ymid) + dx),
                       ack=stg(abs(yco - ymid) + dx), y=stg(yst + G["root_h"] + dx), sflt=stg(abs(yst - yco)),
                       tap=[stg(abs(yrow(f + k) + G["slot_h"] // 2 - yco)) for k in range(z)])
            regs.append(row)
            run(f"c{c} r{r} mid->station (go 20 b)", abs(yst - ymid) + dx, row["go_station"], 20)
            run(f"c{c} r{r} mid->collector (go tag 9 b)", abs(yco - ymid) + dx, row["go_collector"], 9)
            run(f"c{c} r{r} collector->mid (ACK 18 b)", abs(yco - ymid) + dx, row["ack"], 18)
            run(f"c{c} r{r} face->station (y {128 * z} + 1 b)", yst + G["root_h"] + dx, row["y"], 128 * z + 1)
            for k in range(z):
                run(f"c{c} r{r} tile {f + k} tap->collector (2 b)", abs(yrow(f + k) + G["slot_h"] // 2 - yco), row["tap"][k], 2)
        cols.append(dict(column=c, half_octets=lc, head=nh, tail=ntl, regions=regs))
    # cut widths at the corridor (the binding cut): bits of express runs crossing y = corridor, per column and total
    cuts = []
    for col in cols:
        tail = [r for r in col["regions"] if r["first"] >= col["head"]]
        head = [r for r in col["regions"] if r["first"] < col["head"]]
        cuts.append(dict(column=col["column"],
                         corridor_north_edge_bits=sum(r["y_bits"] + 1 for r in tail) + sum(20 + 9 + 18 for r in head),
                         corridor_south_edge_bits=sum(r["y_bits"] + 1 + 20 + 9 + 18 for r in tail),
                         column_head_bits=sum(r["y_bits"] + 1 for r in col["regions"])))
    worst = max(runs, key=lambda x: x["max_stage_um"])
    return dict(schema="opentallas.s81hc.post_express.geometry.v1", ng=ng, head_rows=head_rows, geometry_001um=G,
                source="v13: el1013-s81hc.log 2026-10-13 03:20 PT; post_express_spec.json conditional contract "
                       "9d693102b6204d2f75c682a9add45fadf746614c4600d1ea58303a7ffa3bddfb",
                reach_um=G["reach"] / 100, midpoint_y_um=ymid / 100, sequencer_stages=nt, columns=cols, runs=runs,
                max_stage_um=worst["max_stage_um"], max_stage_run=worst["run"], all_stages_within_reach=all(
                    x["max_stage_um"] <= G["reach"] / 100 for x in runs),
                chain_stations=dict(per_column=max(len(c["regions"]) for c in cols),
                                    note="one registered stage on {reset, fv, fd, cy} at each region head; abuts the "
                                         "first slot of the region (no added wire); needs a station strip in v14"),
                corridor_cuts=cuts,
                cut_note="existing HC corridor bundle 15,660 b and conditional capacity 93,350 tracks are from "
                         "post_express_spec.json conditional_cut_study; the die lead owns the real-view check")


def check_log(p, text):
    bad = []
    seen = 0
    by = {(c["column"], r["region"]): r for c in p["columns"] for r in c["regions"]}
    for m in re.finditer(r"HCX region c=(\d+) r=(\d+) first=(\d+) size=(\d+) go_station=(\d+) go_collector=(\d+) ack=(\d+) "
                         r"y=(\d+) sflt=(\d+)", text):
        c, r, f, z, gs, gc, ak, y, sf = map(int, m.groups())
        e = by[(c, r)]
        seen += 1
        if (f, z, gs, gc, ak, y, sf) != (e["first"], e["size"], e["go_station"], e["go_collector"], e["ack"], e["y"], e["sflt"]):
            bad.append(m.group(0))
    for m in re.finditer(r"HCX tap c=(\d+) r=(\d+) p=(\d+) stages=(\d+)", text):
        c, r, pp, n = map(int, m.groups())
        e = by[(c, r)]
        if e["tap"][pp - e["first"]] != n:
            bad.append(m.group(0))
    m = re.search(r"HCX mid sequencer_stages=(\d+)", text)
    if not m or int(m.group(1)) != p["sequencer_stages"]:
        bad.append("mid")
    return dict(regions_seen=seen, regions_expected=len(by), mismatches=bad, ok=(not bad and seen == len(by)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ng", type=int, default=256)
    ap.add_argument("--log", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    p = plan(a.ng, 10 if a.ng == 256 else 2)
    if a.log:
        p["rtl_check"] = check_log(p, a.log.read_text())
    if a.out:
        a.out.write_text(json.dumps(p, indent=1) + "\n")
    print("regions", sum(len(c["regions"]) for c in p["columns"]), "runs", len(p["runs"]), "max stage um", p["max_stage_um"],
          "(", p["max_stage_run"], ")", "rtl_check", p.get("rtl_check", {}).get("ok"))
    for c in p["columns"]:
        print(" col", c["column"], [(r["size"], r["go_station"], r["ack"], r["y"], r["tap"]) for r in c["regions"]])
    return 0 if p["all_stages_within_reach"] and p.get("rtl_check", {"ok": True})["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
