#!/usr/bin/env python3
"""HBM-NEXT-ATT4 step 3 (2026-10-19): PUBLICATION-PATH bench of the shared 4-lane PV merge tile (ot_hnx_att4_spvm,
ot_hnx_att4_smerge PUBLISH = 1), which the slice bench (att4_bench.py, PUBLISH = 0) does not cover.

Stimulus at the tile pins, in rounds.  Each round, on every residue s (= ring slot s, all lanes share the beat timing)
every lane runs ONE chunk run of 1 .. 4 chunks (LV 3) under the legal record bound of tools/hbm_next/att4_smerge_sched.py
(a lane's chunk events on a residue >= 8 turns apart; aligned / staggered / random lane patterns); chunk sums = random
FP32 vectors (16 words, mixed signs and exponents, never -0: every value the tcpv emits is an RNE adder output).  After
the round's last node is merged (the schedule model's node turn + margin), the compiler-fixed publication requests read
all 32 (lane, slot) nodes: pub_start on a cycle whose residue holds the slot, back to back at word 14 of the previous
stream when the slot repeats (the release merge's publication timing), else >= 18 cycles apart.
Golden per node = csum8 pairwise tree of the run's chunk sums (tools/hgi_sim/lib.py pairwise, == att_pv's chunk merge).
Checks: every requested node is published exactly once, 16 words in order, data bit-exact, pub_tag = the run's last
tag, pub_out_lane / pub_out_slot = the request, no fault.  Verilator 5.050 (the closure daemon's).

  att4_pub_bench.py run --work DIR --out R.json [--rounds 24] [--seed 1019] [--mut 0|1..5]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
from hgi_sim import lib as A  # noqa: E402

_sp = importlib.util.spec_from_file_location("att4_smerge_sched", ROOT / "tools/hbm_next/att4_smerge_sched.py")
S = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(S)

F = np.float32
NL, LV = 4, 3
SRC = ["rtl/hdc/ot_hdc_prefix.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/hbm_next/att/ot_hnx_att4_smerge.sv", "rtl/hbm_next/att/ot_hnx_att4_spvm.sv",
       "rtl/hbm_next/att/tb_hnx_att4_pub.sv"]
VERILATOR = os.environ.get("VERILATOR") or next(
    (c for c in (os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"),) if os.path.exists(c)),
    "verilator")


def lane_runs(rng, kind):
    """one run a lane on one residue: {turn: {lane: (first, last)}}, chunk counts."""
    maxc = 1 << (LV - 1)
    ev, nchunks = {}, {}
    for l in range(NL):
        t = {"aligned": 1, "stagger": 1 + l, "random": 1 + rng.randint(0, 12)}[kind]
        n = maxc if kind == "aligned" else rng.randint(1, maxc)
        nchunks[l] = n
        for c in range(n):
            ev.setdefault(t, {})[l] = (c == 0, c == n - 1)
            t += 8 if kind == "aligned" else 8 + (rng.randint(0, 3) if rng.random() < 0.5 else 0)
    return ev, nchunks


def rand_vec(rng):
    v = np.array([rng.choice((-1, 1)) * rng.uniform(0.5, 2.0) * 2.0 ** rng.randint(-20, 20) for _ in range(16)], dtype=F)
    return v


def make(rounds, seed):
    rng = random.Random(seed)
    recs = {}            # pin cycle -> dict(ev, tags, sums, pub)
    nodes = []           # expected publications in order: (lane, slot, tag, golden words)
    base = 0
    for r in range(rounds):
        kind = ("aligned", "stagger", "random")[r % 3]
        done_turn = 0
        for s in range(8):
            ev, nch = lane_runs(rng, kind)
            sim = S.simulate(ev, NL, LV)
            if sim["faults"]:
                raise SystemExit(f"illegal generated pattern round {r} slot {s}: {sim['faults'][:2]}")
            done_turn = max([done_turn] + [to for (_, to, _) in sim["nodes"]])
            chunks = {l: [] for l in range(NL)}
            for t in sorted(ev):
                cyc = base + 8 * t + s
                rec = recs.setdefault(cyc, dict(ev=0, tags=[0] * NL, sums=[np.zeros(16, dtype=F)] * NL, pub=None))
                rec["sums"] = list(rec["sums"])
                for l, (first, last) in ev[t].items():
                    v = rand_vec(rng)
                    chunks[l].append(v)
                    tag = (1 << 15) | (int(first) << 14) | (int(last) << 13) | (((r * 4 + l) & 0x3FF) << 3) | s
                    rec["ev"] |= 1 << l
                    rec["tags"][l] = tag
                    rec["sums"][l] = v
            for l in range(NL):
                last_tag = (1 << 15) | ((nch[l] == 1) << 14) | (1 << 13) | (((r * 4 + l) & 0x3FF) << 3) | s
                gold = A.pairwise([c.copy() for c in chunks[l]])
                nodes.append(dict(round=r, lane=l, slot=s, tag=last_tag, n=nch[l],
                                  words=[int(x) for x in np.asarray(gold, dtype=F).view(np.uint32)]))
        # publications: after every node of the round is merged (+2 turns margin), slot-major, lane order
        t_pub = base + 8 * (done_turn + 2) + 8
        prev = None
        order = [n for n in nodes if n["round"] == r]
        order.sort(key=lambda n: (n["slot"], n["lane"]))
        for n in order:
            if prev is None:
                c = t_pub
            elif (prev + 16) % 8 == n["slot"] and n["slot"] == prev_slot:
                c = prev + 16                                   # back to back at word 14
            else:
                c = prev + 18
            while c % 8 != n["slot"]:
                c += 1
            recs.setdefault(c, dict(ev=0, tags=[0] * NL, sums=[np.zeros(16, dtype=F)] * NL, pub=None))["pub"] = \
                (n["lane"], n["slot"])
            n["req"] = c
            prev, prev_slot = c, n["slot"]
        base = ((prev + 24) // 8 + 1) * 8                       # next round starts on residue 0 after the last read
    return recs, nodes, base


def write_stim(recs, path):
    lines = []
    for cyc in sorted(recs):
        r = recs[cyc]
        pub = 0 if r["pub"] is None else (1 << 5) | (r["pub"][0] << 3) | r["pub"][1]
        tags = "".join(f"{r['tags'][l]:04x}" for l in reversed(range(NL)))
        sums = "".join("".join(f"{int(w):08x}" for w in reversed(np.asarray(r["sums"][l], dtype=F).view(np.uint32)))
                       for l in reversed(range(NL)))
        lines.append(f"{cyc:08x}{r['ev'] << 4:02x}{pub:02x}{tags}{sums}")
    Path(path).write_text("\n".join(lines) + "\n")
    return len(lines)


def build(work, mut):
    obj = work / f"obj_pub_m{mut}"
    exe = obj / "Vtb_hnx_att4_pub"
    if exe.exists():
        return exe
    cmd = [VERILATOR, "--binary", "-j", "16", "-O1", "-CFLAGS", "-O1", "--x-assign", "fast", "-Wno-fatal", "-Wno-lint",
           "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "128", "--top-module",
           "tb_hnx_att4_pub", f"-GMUT={mut}", "--Mdir", str(obj)] + [str(ROOT / s) for s in SRC]
    for _ in range(2):                                          # one retry on a precompiled-header race
        r = subprocess.run(cmd, capture_output=True, text=True)
        (work / f"build_pub_m{mut}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr)
        if r.returncode == 0:
            return exe
    raise SystemExit(f"build failed (see {work}/build_pub_m{mut}.log)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--rounds", type=int, default=24)
    p.add_argument("--seed", type=int, default=1019)
    p.add_argument("--mut", type=int, default=0)
    a = ap.parse_args(argv)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    recs, nodes, last = make(a.rounds, a.seed)
    stim = work / f"stim_s{a.seed}_r{a.rounds}.hex"
    n = write_stim(recs, stim)
    exe = build(work, a.mut)
    r = subprocess.run([str(exe), f"+STIM={stim}", f"+N={n}", f"+LAST={last}"], capture_output=True, text=True,
                       timeout=3600)
    out = r.stdout + r.stderr
    (work / f"run_m{a.mut}.log").write_text(out)
    streams, cur = [], None
    for ln in out.splitlines():
        if ln.startswith("PUB "):
            _, l, s, w, tg, d = ln.split()
            l, s, w = int(l), int(s), int(w)
            if w == 0:
                cur = dict(lane=l, slot=s, tag=int(tg, 16), words=[])
                streams.append(cur)
            if cur is None or (l, s) != (cur["lane"], cur["slot"]) or w != len(cur["words"]):
                streams.append(dict(bad=ln))
                cur = None
                continue
            cur["words"].append(int(d, 16))
    exp = sorted(nodes, key=lambda x: x["req"])
    mism, bad, word_mism = 0, [], 0
    if len(streams) != len(exp):
        bad.append(f"streams {len(streams)} != requests {len(exp)}")
    for e, g in zip(exp, streams):
        if "bad" in g or (g["lane"], g["slot"], g["tag"]) != (e["lane"], e["slot"], e["tag"]) or len(g["words"]) != 16 \
                or g["words"] != e["words"]:
            mism += 1
            if "words" in g and len(g["words"]) == 16:
                word_mism += sum(int(x != y) for x, y in zip(g["words"], e["words"]))
            if len(bad) < 5:
                bad.append(dict(exp={k: e[k] for k in ("round", "lane", "slot", "tag", "n", "req")},
                                got={k: g.get(k) for k in ("lane", "slot", "tag", "bad")}))
    fault = "FAULT" in out
    ok = r.returncode == 0 and not fault and mism == 0 and len(streams) == len(exp) and len(exp) > 0
    nrun = {k: sum(1 for x in nodes if x["n"] == k) for k in range(1, 5)}
    res = dict(bench="att4_pub", mut=a.mut, seed=a.seed, rounds=a.rounds, nodes=len(exp), streams=len(streams),
               node_mismatches=mism, word_mismatches=word_mism, fault=fault, rc=r.returncode, runs_by_chunks=nrun,
               verilator=VERILATOR, examples=bad, pass_=ok)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(("PASS" if ok else "FAIL") + " HNX_ATT4_PUB " + json.dumps({k: v for k, v in res.items() if k != "examples"}))
    if not ok and bad:
        print("first mismatches: " + json.dumps(bad)[:1500])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
