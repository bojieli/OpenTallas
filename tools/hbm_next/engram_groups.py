#!/usr/bin/env python3
"""HBM-NEXT-CMTP: price the DS Engram layers (1, 14) of the N = 6 MTP verify against the VM size.

Problem (static_check C4, results/arch/hbm_next_1019/cmtp/static): at N = 6 the normal layers peak at ~327k live VM
words, the Engram layers at 470k / 486k; the grown VM (D1: 2^18 + 5 x 30k = 412,144 words) holds all but the two
Engram layers.  Two ways out:
  VM490   grow the VM to >= the Engram peak (~490k words): no cycle cost, area for DIE.
  RGk     issue the two Engram layer segments in ROW GROUPS of k positions (6 / k sequential groups, each an N = k
          programme of that layer; positions in order, so every group sees the KV appends of the groups before it --
          the causal rule is unchanged); weights / experts are re-read per group.  Cost = sum over groups of the
          N = k segment cycles - the N = 6 segment cycles; the VM need = the N = k segment peak + the h / PRE columns
          (20,484 words each) of the 6 - k positions not in the group (they stay resident between groups).
This module measures both on the scheduled timeline (the C4 word-level liveness of static_check, plus a breakdown of
the live words at the peak by writer record, so the cause is named), under the CMTP headline knobs (P = 4, L5 COLL,
union histogram, M1, rpl, HC II 250, grown VM).

    PYTHONPATH=tools python3 tools/hbm_next/engram_groups.py --out results/arch/hbm_next_1019/cmtp/engram_groups.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_next"))

import plane_compiler as PC  # noqa: E402
import static_check as SC  # noqa: E402

VM_GROWN = SC.VM_WORDS + 5 * 30000
COLUMN_WORDS = 20480 + 4          # one position's h + PRE (static_check hpre)
ENGRAM = ("1", "14")


def live_breakdown(seg, s, fps, at):
    """live VM words at cycle `at` by writer record tag (positions folded) -- same liveness rule as SC.c4_vm_live"""
    ex, start, end = s["ex"], s["start"], s["end"]
    VW, VO = SC.VM_WORDS, SC.VM_OFF
    order = sorted(range(len(ex)), key=lambda i: start[i])
    mk = lambda: dict(defined=np.full(VW, -1.0), lastuse=np.full(VW, -1.0), writer=np.full(VW, -1, np.int64))
    copies = defaultdict(mk)
    spans = defaultdict(int)

    def close(c, a, b):
        dfn, lu, wr = c["defined"][a:b], c["lastuse"][a:b], c["writer"][a:b]
        m = (dfn >= 0) & (lu >= 0) & (dfn <= at) & (lu > at)
        for w, k in zip(*np.unique(wr[m], return_counts=True)):
            spans[int(w)] += int(k)
    for i in order:
        rd, wr = fps[i]
        for sp, lo, hi in rd:
            if sp != "VM":
                continue
            cp, a, b = lo // VO, lo % VO, min(hi - (lo // VO) * VO, VW)
            if a >= VW:
                continue
            c = copies[cp]
            d = c["defined"][a:b]
            und = d < 0
            d[und] = 0.0                     # live-in (column or constant): writer -1
            seg_ = c["lastuse"][a:b]
            np.maximum(seg_, np.where(d >= 0, end[i], -1.0), out=seg_)
        for sp, lo, hi in wr:
            if sp != "VM":
                continue
            cp, a, b = lo // VO, lo % VO, min(hi - (lo // VO) * VO, VW)
            if a >= VW:
                continue
            c = copies[cp]
            close(c, a, b)
            c["defined"][a:b] = end[i]
            c["lastuse"][a:b] = -1.0
            c["writer"][a:b] = i
    for c in copies.values():
        close(c, 0, VW)
    by = defaultdict(int)
    for i, w in spans.items():
        if i < 0:
            by["live-in (entering columns h/PRE + constants)"] += w
        else:
            r = seg[ex[i][0]]
            by[f"{r.unit}.{r.op} {re.sub(r'[0-9]+', '#', (r.tag or ''))[:48]}"] += w
    return dict(sorted(by.items(), key=lambda kv: -kv[1])[:14])


def footprints(seg, s):
    """the VM / HBM footprints exactly as static_check.check computes them"""
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import ds_native_timing as DT
    from hgi_sim import timing as T
    dyn = T.Dyn(DT.POS)
    out = []
    for (k, L, L1) in s["ex"]:
        rd, wr = V._footprint(seg[k], dyn, L)
        out.append(([iv for iv in rd if iv[0] in ("VM", "HBM")], [iv for iv in wr if iv[0] in ("VM", "HBM")]))
    return out


def seg_measure(N, union, keys, kv="upper"):
    from hgi_sim import hbm_plane_model as M
    cfg = M.plane_cfg(4 if N > 1 else 1)
    PC.CUR["mode"] = "verify"
    prog, _ = M.ds_compile(N, cfg, union, kv, False)
    M.P5._count_slots(prog)
    M.P5._consumers(prog)
    out = {}
    for key, seg, s in SC.schedule_segments(prog, set(keys)):
        r = SC.check(seg, s, n_rows=N, ring=(256, N) if N > 1 else (128, 1), vm_capacity={"grown": VM_GROWN})
        out[str(key)] = dict(cycles=round(s["total_cycles"], 1), PASS=r["PASS"], counts=r["counts"],
                             vm_peak=r["vm"]["peak_words"], vm_peak_at=r["vm"]["peak_at"], _seg=seg, _s=s)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    from hgi_sim import hbm_plane_model as M
    st = M.load_stats(PC.STATS)
    PC.CUR["hist"] = PC.lane_hists()
    PC.apply_knobs(PC.Knobs(**PC.HEAD))
    vu = st["verify_union"]
    keys = list(ENGRAM) + ["0"]
    n6 = seg_measure(6, vu[6]["mean"], keys)
    # breakdown at the N = 6 peaks (footprints as the check computes them)
    res = dict(schema="opentallas.hbm_next_1019.cmtp.engram_groups.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, knobs=PC.Knobs(**PC.HEAD).tag(),
        vm_grown_words=VM_GROWN, column_words=COLUMN_WORDS, n6={}, groups={})
    for k, r in n6.items():
        seg, s = r.pop("_seg"), r.pop("_s")
        fps = footprints(seg, s)
        r["live_at_peak_by_writer"] = live_breakdown(seg, s, fps, r["vm_peak_at"])
        res["n6"][k] = r
        print("N6 seg", k, r["cycles"], "peak", r["vm_peak"], json.dumps(r["live_at_peak_by_writer"])[:600], flush=True)
    for k_ in (2, 3):
        u = vu[k_]["mean"] if k_ in vu else (vu[2]["mean"] + vu[4]["mean"]) / 2
        g = seg_measure(k_, u, ENGRAM)
        G = 6 // k_
        row = dict(group_rows=k_, groups=G, union=u, union_basis="MTP-STATS consecutive_verify" if k_ in vu
                   else "interpolated N = 2 / 4", layers={})
        for L in ENGRAM:
            r = g[L]
            r.pop("_seg"), r.pop("_s")
            need = r["vm_peak"] + (6 - k_) * COLUMN_WORDS
            row["layers"][L] = dict(seg_cycles_N=r["cycles"], grouped_cycles=round(G * r["cycles"], 1),
                                    n6_cycles=n6[L]["cycles"], delta_cycles=round(G * r["cycles"] - n6[L]["cycles"], 1),
                                    vm_peak_group=r["vm_peak"], vm_need=need, fits_grown=need <= VM_GROWN,
                                    PASS=r["PASS"], counts=r["counts"])
        row["delta_cycles_per_verify"] = round(sum(x["delta_cycles"] for x in row["layers"].values()), 1)
        res["groups"][f"RG{k_}"] = row
        print(f"RG{k_}", json.dumps(row)[:800], flush=True)
    srcs = ["tools/hbm_next/engram_groups.py", "tools/hbm_next/static_check.py", "tools/hbm_next/plane_compiler.py",
            "tools/hgi_sim/ds_mtp_verify.py", "tools/hgi_sim/timing.py"]
    res["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
