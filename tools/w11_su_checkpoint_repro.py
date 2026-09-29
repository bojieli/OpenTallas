#!/usr/bin/env python3
"""W11: the stream unit's reducer TAP hazard (ot_hdc_v41x_vec checkpoint rule), reproduced in two ops.

rtl_hdc_v41x_vec_campaign's random programs failed 3 of 40 seeds (N16 seeds 11 and 20, N64 seed 116): one
wrong reducer result and a unit fault each.  Every failure is a reducing op that does NOT span vectors
(its result taps the reducer tree at level lt) followed back to back by a SPANNING reduction with a
shallower tap (dT smaller).  Both items leave the tree through the one tap multiplexer
(ot_hdc_v41x_vec_red: tap_multi / res_multi), and the controller ordered only spanning ops at the tap
(checkpoint T was armed by spanning ops alone), so the second op's first item reached the tap in the same
cycle as, or before, the first op's last item.

This tool replays, for each failing seed, the random program's ops (k-1, k) alone on the vector-unit bench:
  chained   the campaign's schedule (no wait between the two ops): the hazard
  idle      op k waits for the unit to be idle: the control
and the whole failing seeds.  Writes results/rtl/w11_su_checkpoint_<label>.json.
    python3 tools/w11_su_checkpoint_repro.py --label bug --scratch /tmp/.../repro
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_vec_campaign as C   # noqa: E402

# (N, M, seed, lo, k): op k of the filtered random program is the spanning reduction; op lo the packed one
# (seed 116: a non-reducing op of 2 vectors sits between them)
CASES = [(16, 8, 11, 37, 38), (16, 8, 20, 25, 26), (64, 16, 116, 22, 24)]
SOURCES = [*C.LIB, *C.RTL, C.TB, C.FIELDS_SVH, C.HARNESS, Path(__file__).resolve(), *C.TOOLS]


def program(seed, N, M, nops=40):
    """The random campaign's program for a seed, filtered exactly as random_campaign does."""
    rng = np.random.default_rng(seed)
    alloc = C.Alloc(64, (1 << C.VMA) - 64)
    ops, init = C.random_program(rng, N, M, nops, alloc)
    mem0 = C.fresh_mem(rng, init)
    keep, mm = [], mem0.copy()
    for f in ops:
        lay = C.layout(f, N, M)
        t = mm.copy()
        okf, *_ = C.ref_op(dict(f), t)
        if okf and not lay["bad"]:
            keep.append(f)
            mm = t
    return keep, mem0


def desc(f, N, M):
    lay = C.layout(f, N, M)
    keys = ("nout", "nin", "red", "redsq", "redwhole", "redtree", "sfu", "m1", "dst")
    return dict(fields={k: int(f[k]) for k in keys}, span=bool(lay["span"]), packed=bool(lay["packed"]),
                wnf=bool(lay["wnf"]), S=lay["S"], tap_level=lay["lt"], time_levels=lay["L"] if lay["span"] else 0,
                vectors=lay["nv"], model_emit_to_result=lay["dR"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="bug (before the fix) or fix (after)")
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--exe16", type=Path, help="a built tb_hdc_v41x_vec at N16/M8 of these sources")
    ap.add_argument("--exe64", type=Path)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    exes, builds = {16: args.exe16, 64: args.exe64}, {}
    for N, M in ((16, 8), (64, 16)):
        if not exes[N]:
            exes[N], builds[f"N{N}"] = C.build(N, M, args.scratch / f"obj_{N}_{M}")
    rows = []
    for N, M, seed, lo, k in CASES:
        keep, mem0 = program(seed, N, M)
        m = mem0.copy()
        for f in keep[:lo]:
            C.ref_op(dict(f), m)
        row = dict(N=N, M=M, seed=seed, ops=[lo, k], first=desc(keep[lo], N, M), second=desc(keep[k], N, M),
                   between=[desc(f, N, M) for f in keep[lo + 1:k]])
        for mode in ("chained", "idle"):
            pair = [dict(f) for f in keep[lo:k]] + [dict(keep[k], w_idle=1) if mode == "idle" else dict(keep[k])]
            c, tr, sops, lays = C.run_program(exes[N], args.scratch / f"s{seed}_{mode}", m, pair, N, M)
            em0, _, rs0 = C.op_trace(tr, 0)
            em1, _, rs1 = C.op_trace(tr, k - lo)
            row[mode] = dict(c, second_first_emit_after_first_last_emit=(em1[0] - em0[-1]) if em0 and em1 else None,
                             first_last_result=rs0[-1] if rs0 else None, second_results=rs1)
        c, tr, sops, lays = C.run_program(exes[N], args.scratch / f"s{seed}_whole", mem0, keep, N, M)
        row["whole_seed"] = dict(c, ops=len(keep))
        rows.append(row)
        print(json.dumps({k_: row[k_] for k_ in ("N", "seed", "ops")}), row["chained"]["pass_"], row["idle"]["pass_"],
              row["whole_seed"]["pass_"], flush=True)
    rec = dict(schema="opentallas.rtl.w11_su_checkpoint/1", label=args.label,
               generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               hazard="a non-spanning reducing op followed by a spanning reducing op with a shallower tap: both "
                      "items leave through the reducer's one tap; checkpoint T was armed by spanning ops only",
               cases=rows, builds=builds,
               all_pass=all(r["chained"]["pass_"] and r["idle"]["pass_"] and r["whole_seed"]["pass_"] for r in rows),
               hazard_reproduced=any(not r["chained"]["pass_"] for r in rows),
               controls_pass=all(r["idle"]["pass_"] for r in rows))
    h = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    d = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                       capture_output=True, text=True)
    rec["git_head"] = h.stdout.strip() if h.returncode == 0 else os.environ.get("OT_GIT_HEAD", "")
    rec["git_dirty_tracked_files"] = [x[3:] for x in d.stdout.splitlines()] if d.returncode == 0 else "unknown"
    rec["input_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
    out = ROOT / f"results/rtl/w11_su_checkpoint_{args.label}.json"
    out.write_text(json.dumps(rec, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print("wrote", out, "all_pass", rec["all_pass"], "reproduced", rec["hazard_reproduced"])


if __name__ == "__main__":
    main()
