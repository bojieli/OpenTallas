#!/usr/bin/env python3
"""Cycle model of the hardwired decode core, calibrated against its RTL.

Replays a program (tools/hdc_program.py) through a model of the sequencer and
both units -- in-order issue, barriers (both units idle), chases (the other
unit's latest op has made N progress), the matrix engine's fixed element loop
and result latency, the stream unit's per-class depth and same-class overlap,
the reducer's tail -- and returns per-instruction issue cycles and the token's
cycle count.  The constants are the RTL's (see `calibrate`, which fits and
checks them against a Verilator issue trace).  Because the model needs only
the program's shapes, it prices dimensions the RTL simulator cannot reach in
reasonable time, e.g. full Qwen3-8B (`--model qwen3-8b`).
"""
import argparse
import json
import re
from pathlib import Path

import hdc_isa as I

ROOT = Path(__file__).resolve().parents[1]
IL = I.INTERLEAVE

# RTL constants (cycles); fitted by `calibrate` and fixed here.
# Fitted to the reduced vehicle's Verilator issue trace at 4 groups: 32,191
# model cycles against 32,196 RTL cycles, every issue within 7 cycles.
K = dict(seq_gap=5,        # go -> next go, sequencer fetch/decode (S_GO..S_ISSUE)
         me_start=1,       # go -> first element issued
         me_lat=16,        # element issue -> its result written (memory stage, lanes, output registers)
         me_tree=5,        # per split-tree level
         su_start=1,
         su_depth={I.SFU_NONE: 29, I.SFU_EXP: 121, I.SFU_RECIP: 75, I.SFU_RSQRT: 90, I.SFU_SIGM: 172},
         red_tail=32,      # last element retired -> reducer result written
         idle_reg=2)       # last write -> registered idle seen by the sequencer


def dyn_values(pos, token=0, H=128, half=8, HD=16):
    W = I.W_LANES
    return [0, token * H, pos * half, (pos // W) * HD * W + pos % W, pos * HD, pos + 1, pos // W + 1]


def simulate(prog, pos, groups=I.GROUPS, k=K, trace=False, dyn_shape=None, attn_groups=1, su_width=1):
    """attn_groups / su_width > 1 are PROJECTIONS of design options the RTL does
    not have yet: KV-sourced ops spread over that many lane groups (each taking
    its own heads), and a stream unit retiring su_width elements per cycle."""
    dyn = dyn_values(pos, **(dyn_shape or {}))
    t = 0                              # sequencer time: earliest next issue
    me_free = su_free = 0              # unit accepts a new op from here
    me_idle = su_idle = 0              # unit fully drained at
    su_cls, su_cls_idle = None, 0
    me_slot_t = []                     # latest ME op: time each result slot is written
    su_el_t = None                     # latest SU op: (first write time, elements)
    issues = []
    for f in prog:
        f = {name: f.get(name, 0) for name, _ in I.FIELDS}
        u = f["unit"]
        if u == I.UNIT_END:
            t = max(t, me_idle, su_idle) + k["idle_reg"]
            break
        ready = t
        if f["barrier"]:
            ready = max(ready, me_idle + k["idle_reg"], su_idle + k["idle_reg"])
        elif f["chase"]:
            n = f["chase_n"]
            if u == I.UNIT_ME:
                first, cnt = su_el_t
                ready = max(ready, first + min(n, cnt) - 1 + 1)
            else:
                ready = max(ready, me_slot_t[min(n, len(me_slot_t)) - 1] + 1)
        if u == I.UNIT_ME:
            go = max(ready, me_free)
            split = 0 if f["me_wsrc"] else f["me_split"]
            rounds = f["me_tiles"] + dyn[f["me_d_tiles"]]
            if f["me_wsrc"] and attn_groups > 1:
                rounds = -(-rounds // attn_groups)
            kc = f["me_k"] + dyn[f["me_d_k"]]
            n_el = rounds * kc * IL
            e0 = go + k["me_start"]
            lat = k["me_lat"] + k["me_tree"] * (groups.bit_length() - 1)
            me_slot_t = [e0 + r * kc * IL + (kc - 1) * IL + j + lat for r in range(rounds) for j in range(IL)]
            me_free = e0 + n_el
            me_idle = max(me_idle, me_slot_t[-1])
        else:
            cls = f["sfu"]
            go = max(ready, su_free)
            if su_cls is not None and cls != su_cls:
                go = max(go, su_cls_idle)
            n_el = -(-f["su_nout"] * (f["su_nin"] + dyn[f["su_d_nin"]]) // su_width)
            e0 = go + k["su_start"]
            d = k["su_depth"][cls]
            su_el_t = (e0 + d, n_el)
            last = e0 + n_el - 1 + d
            tail = last + (k["red_tail"] if f["red"] else 0)
            su_free = e0 + n_el
            su_idle = max(su_idle, tail)
            su_cls, su_cls_idle = cls, last
        issues.append(go)
        t = go + k["seq_gap"]
    return issues, t


# Model shapes (from each model's released config.json).
SHAPES = {
    "qwen3-8b": dict(H=4096, L=36, NH=32, KV=8, HD=128, FF=12288, V=151936),   # Qwen/Qwen3-8B
    "qwen3-reduced": dict(H=128, L=4, NH=8, KV=2, HD=16, FF=384, V=4096),
}


class ShapeLayout:
    """What build_program needs from a Layout, from shapes alone (no weights):
    matrix tiling and K-split exactly as Layout.place_matrix derives them."""

    def __init__(self, shape, groups):
        import hdc_golden as G
        self.H, self.L, self.NH, self.KV = shape["H"], shape["L"], shape["NH"], shape["KV"]
        self.HD, self.FF, self.V = shape["HD"], shape["FF"], shape["V"]
        self.half, self.eps, self.emb_word = self.HD // 2, 1e-6, 0
        W = I.W_LANES
        self.TW = 1 << 20

        def mat(n, k):
            split = G.split_for(n, k, groups, W, IL)
            tiles = -(-n // (W * IL))
            return dict(base=0, n=n, k=k // split, tiles=-(-tiles // (groups // split)), split=split)
        self.mat = {}
        for L in range(self.L):
            self.mat[(L, "qkv")] = mat((self.NH + 2 * self.KV) * self.HD, self.H)
            self.mat[(L, "o")] = mat(self.H, self.NH * self.HD)
            self.mat[(L, "gu")] = mat(2 * self.FF, self.H)
            self.mat[(L, "down")] = mat(self.H, self.FF)
        self.mat["lm_head"] = mat(self.V, self.H)
        self.cb = {k: 0 for k in [(L, n) for L in range(self.L) for n in ("in", "qk", "post")] + ["final", "rope"]}

    def k_elem(self, L, g, t, d):
        return ((L * self.KV + g) * self.TW + t) * self.HD + d

    def v_elem(self, L, g, t, d):
        return ((L * self.KV + g) * self.TW + t) * self.HD + d


def price(model, groups, pos, ghz, attn_groups=1, su_width=1):
    """Cycles per token of `model` on a core of `groups` 16-lane groups."""
    import hdc_program as P
    shape = SHAPES[model]
    lay = ShapeLayout(shape, groups)
    prog = P.build_program(lay)
    dyn_k = dict(H=shape["H"], half=shape["HD"] // 2, HD=shape["HD"])
    issues, cycles = simulate(prog, pos, groups=groups, dyn_shape=dyn_k, attn_groups=attn_groups,
                              su_width=su_width)
    me_busy = sum(1 for f in prog if f.get("unit") == I.UNIT_ME)
    return {"model": model, "groups": groups, "lanes": groups * I.W_LANES, "position": pos,
            "instructions": len(prog), "cycles_per_token": cycles,
            "tokens_per_s_at_clock": round(ghz * 1e9 / cycles, 2), "clock_ghz": ghz,
            "projection": {"attn_groups": attn_groups, "su_width": su_width}}


def calibrate(trace_path, prog, pos):
    txt = Path(trace_path).read_text()
    rtl = [int(c) for c, _ in re.findall(r"ISSUE cyc=(\d+) pc=(\d+)", txt)]
    rtl_total = int(re.search(r"cycles=(\d+)", txt).group(1))
    model, total = simulate(prog, pos)
    diffs = [m - r for m, r in zip(model, rtl)]
    return {"rtl_cycles": rtl_total, "model_cycles": total, "error_pct": 100.0 * (total - rtl_total) / rtl_total,
            "max_issue_skew": max(map(abs, diffs)), "instructions": len(rtl)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trace", help="Verilator +TRACE log to calibrate against (reduced vehicle)")
    ap.add_argument("--model", choices=sorted(SHAPES), help="price a model's shapes instead")
    ap.add_argument("--groups", type=int, nargs="+", default=[I.GROUPS])
    ap.add_argument("--pos", type=int, default=1024)
    ap.add_argument("--ghz", type=float, default=1.1)
    ap.add_argument("--attn-groups", type=int, default=1, help="PROJECTION: attention over this many groups")
    ap.add_argument("--su-width", type=int, default=1, help="PROJECTION: stream-unit elements per cycle")
    args = ap.parse_args()
    if args.model:
        for g in args.groups:
            print(json.dumps(price(args.model, g, args.pos, args.ghz, min(args.attn_groups, g), args.su_width)))
        return
    import hdc_program as P
    model, prompt, expected, cache = P.golden_state()
    lay = P.Layout(model)
    prog = P.build_program(lay)
    if args.trace:
        print(json.dumps(calibrate(args.trace, prog, len(prompt) - 1), indent=1))
    else:
        print(simulate(prog, len(prompt) - 1)[1])


if __name__ == "__main__":
    main()
