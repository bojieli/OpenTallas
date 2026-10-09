#!/usr/bin/env python3
"""MTP rollback exactness: multi-step speculative decode with mixed accept counts, golden-structured
reference vs the RTL rollback units (stream mtp-rollback, 2026-10-08).

WHAT IS PROVEN.  KV rollback of rejected MTP positions is a STORAGE question: the arithmetic of a
position is the golden's (bit-exact elsewhere: field phases, the reduced-core one-step run, the ISA),
and greedy speculative = greedy is a golden property (tools/hdc_golden_v41.py generate_spec, 328b5fff).
What the hardware adds is WHERE every speculative state lives and how a rejection is undone.  This
bench isolates exactly that, on the smallest vehicle that contains it (AGENTS.md "simulate the minimum
component"): a toy decode model with V4.1's state DATAFLOW -- every read a V4.1 position makes of
earlier positions' state, in V4.1's order -- and a 32-bit mixing function in place of the arithmetic,
so any stale, clobbered, missing or misordered state word changes the targets, the accept count, the
emitted tokens and the state digests.

  layer 0  window-only layer (V4.1 L0; compress_ratio 0)       window row write, window read (W rows)
  layer 1  Engram layer (L1 / L14)                              NG-token history read, then window
  layer 2  ratio-2 KV + index source (L2 / L8 / L14)            window; compressor open-group slot,
                                                                 group pooling (ckv + index key);
                                                                 indexer scan of keys 0..n-1, select
  layer 3  ratio-1 KV + index source (L20)                      window; compressor (r = 1); indexer
  DSpark   3 stages' window caches `dsk` (seeded from every verified position's main hidden state,
           read by the drafter at the anchor in ring-slot order -- golden dspark_window)

The reference keeps the golden's state STRUCTURE (lists indexed by position / group, the compressor
`slots` + `slotrec`) and rolls back with the golden's own Model.truncate (imported, unmodified).  The RTL
bench (rtl/test/mtp_rollback/tb_mtp_rollback.sv) keeps every state in the hardware units (rings,
spec-state addresses, the HBM window writer / reader / DRAM) and rolls back ONLY by the commit pointer
n = q + 2 + a from ot_mtp_commit.  The bench computes its own targets (ot_hdc_accept decides a) and feeds
its own bonus token forward, so a state error propagates; at every step it checks the draft-side reads,
the targets, a, and a digest of every committed state against this reference.

    python3 tools/mtp_rollback_bench.py gen  --out DIR [--window 128] [--prompt 24] [--steps 160] [--seed 1]
    python3 tools/mtp_rollback_bench.py run  --out DIR --backend rom|hbm [--mutant NAME] [--sim verilator|iverilog]
    python3 tools/mtp_rollback_bench.py campaign --out DIR [--record results/rtl/mtp_rollback_20261008/record.json]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import subprocess
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402  (Model.truncate only; no weights are loaded)

M = 0xFFFFFFFF
NG, NST, G = 4, 3, 5
PADV = 0xFFFFFFFF
LT = ("W", "E", "C", "C")               # layer kinds
RATIO = [0, 0, 2, 1]                    # compress ratio per toy layer (golden self.ratio)
KV_SRC = [2, 3]                         # golden self.kv_src
VMASK = 0xFFF                           # target = (h >> 8) & VMASK (17-bit token width in RTL)
STUB = types.SimpleNamespace(ratio=RATIO, kv_src=KV_SRC)


def mix(a, b):
    x = (a ^ ((b + 0x9E3779B9 + ((a << 6) & M) + (a >> 2)) & M)) & M
    x = (x * 0x85EBCA6B) & M
    return x ^ (x >> 13)


def fold(d, vals):
    for v in vals:
        d = mix(d, v)
    return d


class Ref:
    """Golden-structured toy decode state; rollback = hdc_golden_v41.Model.truncate."""

    def __init__(self, W):
        self.W = W
        self.st = {"tokens": [], "win": [[] for _ in LT], "ckv": {s: [] for s in KV_SRC},
                   "ik": {s: [] for s in KV_SRC}, "slots": {s: [] for s in KV_SRC},
                   "slotrec": {s: {} for s in KV_SRC}, "dsk": [[] for _ in range(NST)]}

    def hist(self, p):
        t = self.st["tokens"]
        return [t[p - k] if p - k >= 0 else PADV for k in range(NG)]

    def dspark_window(self, s, anchor):      # golden Model.dspark_window
        W = self.W
        ps = sorted(range(max(0, anchor + 1 - W), anchor + 1), key=lambda p: p % W)
        return [self.st["dsk"][s][p] for p in ps]

    def layer(self, L, ctx):
        st, p, h = self.st, ctx["pos"], ctx["h"]
        if LT[L] == "E":
            h = fold(h, self.hist(p))
        row = mix(h, 0x100 + L)
        st["win"][L].append(row)
        assert len(st["win"][L]) == p + 1
        h = fold(h, st["win"][L][-self.W:])
        if L in KV_SRC:
            r = RATIO[L]
            sv = mix(h, 0x200 + L)
            if r == 1:
                latent = sv
            else:
                st["slots"][L].append(sv)
                st["slotrec"][L][p] = sv
                latent = None
                if (p + 1) % r == 0:
                    latent = fold(0x77, st["slots"][L])
                    st["slots"][L] = []
            if latent is not None:
                st["ckv"][L].append(latent)
                st["ik"][L].append(mix(latent, 0x55))
            n = (p + 1) // r
            assert len(st["ik"][L]) == n
            if n:
                d = fold(h, st["ik"][L][:n])
                h = mix(d, st["ckv"][L][d % n])
        ctx["h"] = h

    def forward(self, toks, pos0):
        st = self.st
        st["tokens"].extend(toks)
        assert len(st["tokens"]) == pos0 + len(toks)
        ctxs = [{"pos": pos0 + j, "h": mix(0x1234, t)} for j, t in enumerate(toks)]
        for L in range(len(LT)):                      # layer-major (the verify pass order)
            for c in ctxs:
                self.layer(L, c)
        tg = []
        for c in ctxs:
            tg.append((c["h"] >> 8) & VMASK)
            for s in range(NST):
                assert len(st["dsk"][s]) == c["pos"]
                st["dsk"][s].append(mix(c["h"], 0x400 + s))
        return tg

    def truncate(self, n):
        V.Model.truncate(STUB, self.st, n)

    def draft_digest(self, q):
        assert len(self.st["dsk"][0]) == q + 1
        return [fold(0x5151 + s, self.dspark_window(s, q)) for s in range(NST)]

    def state_digests(self):
        st, n = self.st, len(self.st["tokens"])
        out = [fold(0x3000 + L, st["win"][L][-self.W:]) for L in range(len(LT))]
        out.append(fold(0x3102, st["slots"][2]))
        out.append(fold(0x3200, self.hist(n - 1)))
        out += [fold(0x3300 + s, self.dspark_window(s, n - 1)) for s in range(NST)]
        out += [fold(fold(0x3400 + L, st["ckv"][L]), st["ik"][L]) for L in KV_SRC]
        return out


DIGEST_NAMES = ["win_L0", "win_L1", "win_L2", "win_L3", "cmp_open_slot_L2", "engram_hist",
                "dsk_s0", "dsk_s1", "dsk_s2", "ckv_ik_L2", "ckv_ik_L3"]


def gen(out: Path, W: int, prompt_len: int, steps: int, seed: int):
    rng = random.Random(seed)
    ref = Ref(W)
    lines, passes = [], []
    prompt = [rng.randrange(VMASK + 1) for _ in range(prompt_len)]
    # prefill: one position a pass (g = 0), explicit token
    for p, t in enumerate(prompt):
        tg = ref.forward([t], p)
        ref.truncate(p + 1)
        lines.append(f"P 0 {p - 1 & M:x} {t:x} 0")
        lines.append(f"E 0 0 0 0 0 {tg[0]:x}")
        lines.append("S " + " ".join(f"{d:x}" for d in ref.state_digests()))
    q, y = prompt_len - 1, tg[0]
    out_tokens = [y]
    # accept schedule: every a in 0..g appears, mixed order; some steps with g < G
    sched = []
    for k in range(steps):
        g = G if rng.random() < 0.8 else rng.randrange(1, G + 1)
        a = [0, G, 1, 4, 2, 3][k % 6] if k < 12 else rng.randrange(g + 1)
        sched.append((g, min(a, g)))
    for g, a in sched:
        dd = ref.draft_digest(q)
        # forced drafter: d_i = t_{i-1} for i <= a, d_{a+1} != t_a, rest arbitrary (each pass on a copy)
        drafts = []
        for i in range(g):
            trial = copy.deepcopy(ref)
            tg = trial.forward([y] + drafts + [0] * (g - len(drafts)), q + 1)
            if i < a:
                drafts.append(tg[i])
            elif i == a:
                drafts.append(tg[i] ^ 1)
            else:
                drafts.append(rng.randrange(VMASK + 1))
        tg = ref.forward([y] + drafts, q + 1)
        acc = 0
        while acc < g and drafts[acc] == tg[acc]:
            acc += 1
        assert acc == a, (acc, a)
        ref.truncate(q + 2 + a)
        passes.append(dict(anchor=q, g=g, accepted=a))
        lines.append(f"P 1 {q:x} {y:x} {g} " + " ".join(f"{d:x}" for d in drafts))
        lines.append(f"E 1 {dd[0]:x} {dd[1]:x} {dd[2]:x} {a} " + " ".join(f"{t:x}" for t in tg))
        lines.append("S " + " ".join(f"{d:x}" for d in ref.state_digests()))
        out_tokens += tg[:a + 1]
        q, y = q + 1 + a, tg[a]
    # the golden property on the toy: speculative tokens == plain greedy tokens
    plain = Ref(W)
    for p, t in enumerate(prompt):
        tg = plain.forward([t], p)
    ar = [tg[0]]
    for p in range(prompt_len, prompt_len + len(out_tokens) - 1):
        ar.append(plain.forward([ar[-1]], p)[0])
    assert ar == out_tokens, "toy speculative != toy greedy"
    out.mkdir(parents=True, exist_ok=True)
    (out / "stim.txt").write_text("\n".join(lines) + "\nX\n")
    hist = {a: sum(1 for p in passes if p["accepted"] == a) for a in range(G + 1)}
    meta = dict(window=W, gamma=G, ng=NG, nst=NST, prompt=prompt_len, steps=steps, seed=seed,
                positions=q + 1, emitted=len(out_tokens), accept_hist=hist,
                g_hist={g: sum(1 for p in passes if p["g"] == g) for g in range(1, G + 1)},
                spec_equals_greedy=True, stim_sha256=hashlib.sha256((out / "stim.txt").read_bytes()).hexdigest())
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


# ---------------------------------------------------------------- RTL runs
ROM_SRC = ["rtl/hdc/ot_hdc_accept.sv", "rtl/mtp/rollback/ot_mtp_commit.sv", "rtl/mtp/rollback/ot_mtp_pos_ring.sv",
           "rtl/mtp/rollback/ot_mtp_cmp_slot_ring.sv", "rtl/mtp/rollback/ot_mtp_hist_ring.sv"]
HBM_SRC = ["rtl/hdc/ot_hdc_accept.sv", "rtl/mtp/rollback/ot_mtp_commit.sv", "rtl/gpu/dshbm/ot_dshbm_spec_state.sv",
           "rtl/hdc/ot_hdc_prefix.sv", "rtl/experimental/ctl_spec_seed8_20261005/ot_dshbm_spec_state_f_token_edge.sv",
           "rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_spec.sv", "rtl/hbm_accel/service/ot_hbm_accel_dswin_rd.sv"]
TB = "rtl/test/mtp_rollback/tb_mtp_rollback.sv"

# mutants: name -> (backend, parameter overrides).  Every mutant must FAIL.
MUTANTS = {
    "rom": {
        "rom_win_ring_eq_W": dict(WRR="W"),                  # window ring R = W (AR sizing), tag check on
        "rom_win_ring_eq_W_notag": dict(WRR="W", TAGCHK=0),  # same, no tag check: silent wrong data
        "rom_open_slot_no_restore": dict(MUT_OPEN_REG=1),    # compressor open group as one AR register
        "rom_engram_hist_no_restore": dict(MUT_APPEND=1),    # Engram history appends, never rewinds
        "rom_dsk_ring_eq_W": dict(DRR="W"),                  # DSpark window rows in a W-slot ring
        "rom_commit_off_by_one": dict(MUT_OFF=1),
    },
    "hbm": {
        "hbm_win_mod_W_asbuilt": dict(WINSL="W"),            # writer + read stream at pos mod W (as built: 128)
        "hbm_slot_ring_eq_r": dict(SSR=2),                   # spec-state compressor slot ring SR = r
        "hbm_tok_ring_eq_NG": dict(STR=4),                   # spec-state token ring TR = NG
        "hbm_commit_off_by_one": dict(MUT_OFF=1),
        "hbm_key_shadow_reload_on_block_open": dict(MUT_SHRELOAD=1),   # as-built shadow policy under MTP
    },
}


def params(W, over):
    p = dict(W=W, WRR=2 * W, DRR=2 * W, TAGCHK=1, MUT_OPEN_REG=0, MUT_APPEND=0, MUT_OFF=0,
             WINSL=2 * W, SSR=16, STR=16, MUT_SHRELOAD=0)
    for k, v in over.items():
        p[k] = W if v == "W" else v
    return p


def run(out: Path, backend: str, mutant: str | None, sim: str, spec_f: bool = False, tag: str | None = None):
    meta = json.loads((out / "meta.json").read_text())
    W = meta["window"]
    over = MUTANTS[backend][mutant] if mutant else {}
    p = params(W, over)
    name = tag or (mutant or f"{backend}_good") + ("_specf" if spec_f else "")
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    defs = (["+define+HBM_BACKEND"] if backend == "hbm" else []) + (["+define+SPEC_F"] if spec_f else [])
    srcs = [str(ROOT / s) for s in (HBM_SRC if backend == "hbm" else ROM_SRC)] + [str(ROOT / TB)]
    gp = {**p, "STIM": f'"{(out / "stim.txt").resolve()}"', "MAXCYC": 5_000_000 if W < 128 else 400_000_000}
    t0 = time.time()
    if sim == "verilator":
        vl = os.environ.get("VERILATOR", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
        cmd = [vl, "--binary", "--timing", "-Wno-fatal", "-Wno-WIDTH", "-Wno-lint", "-Wno-style", "-O2", "-j", "4",
               "--top-module", "tb_mtp_rollback", "--Mdir", str(d / "obj")] + \
              [x.replace("+define+", "-D") for x in defs] + [f"-G{k}={v}" for k, v in gp.items()] + srcs
        b = subprocess.run(cmd, capture_output=True, text=True)
        (d / "build.log").write_text(b.stdout + b.stderr)
        if b.returncode:
            return dict(name=name, verdict="BUILD_FAIL")
        r = subprocess.run([str(d / "obj" / "Vtb_mtp_rollback")], capture_output=True, text=True)
    else:
        cmd = ["iverilog", "-g2012", "-s", "tb_mtp_rollback", "-o", str(d / "sim.vvp")] + \
              [x.replace("+define+", "-D") for x in defs] + [f"-Ptb_mtp_rollback.{k}={v}" for k, v in gp.items()] + srcs
        b = subprocess.run(cmd, capture_output=True, text=True)
        (d / "build.log").write_text(b.stdout + b.stderr)
        if b.returncode:
            return dict(name=name, verdict="BUILD_FAIL")
        r = subprocess.run(["vvp", "-n", str(d / "sim.vvp")], capture_output=True, text=True)
    (d / "run.log").write_text(r.stdout + r.stderr)
    res = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    first = [l for l in r.stdout.splitlines() if l.startswith("MISMATCH")][:3]
    v = res[-1].split()[1] if res else "NO_RESULT"
    kv = dict(x.split("=", 1) for x in res[-1].split()[2:]) if res else {}
    return dict(name=name, backend=backend, mutant=mutant, spec_state="f_token_edge_fix1" if spec_f else "as_built",
                params=p, verdict=v, expect="FAIL" if mutant else "PASS", ok=(v == ("FAIL" if mutant else "PASS")),
                first_mismatches=first, wall_s=round(time.time() - t0, 1), **kv)


def campaign(out: Path, sim: str, record: Path | None, jobs: int):
    configs = [("w128", dict(W=128, prompt_len=24, steps=170, seed=1)),
               ("w8", dict(W=8, prompt_len=6, steps=60, seed=2))]
    metas, tasks = {}, []
    for cname, c in configs:
        cd = out / cname
        metas[cname] = gen(cd, c["W"], c["prompt_len"], c["steps"], c["seed"])
        for backend in ("rom", "hbm"):
            tasks.append((cd, backend, None, False))
            if backend == "hbm":
                tasks.append((cd, backend, None, True))
            for m in MUTANTS[backend]:
                tasks.append((cd, backend, m, False))
    with ThreadPoolExecutor(jobs) as ex:
        results = list(ex.map(lambda t: {**run(t[0], t[1], t[2], sim, t[3]), "config": t[0].name}, tasks))
    allok = all(r["ok"] for r in results)
    rec = dict(stream="mtp-rollback", date="2026-10-08", tool="tools/mtp_rollback_bench.py", simulator=sim,
               configs=metas, digests_checked_every_step=DIGEST_NAMES,
               checks_every_step=["draft-side DSpark window reads (3 stages)", "targets t_0..t_g", "accept count a",
                                  "emitted tokens (bench feeds its own bonus forward)"] + DIGEST_NAMES,
               results=results, all_good_pass_all_mutants_fail=allok,
               sources={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                        for s in sorted(set(ROM_SRC + HBM_SRC + [TB, "tools/mtp_rollback_bench.py",
                                                                  "tools/hdc_golden_v41.py"]))})
    if record:
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps(rec, indent=1) + "\n")
    for r in results:
        print(f"{r['config']:5s} {r['name']:34s} {r['verdict']:10s} expect {r['expect']:4s} "
              f"{'ok' if r['ok'] else 'WRONG'}  {r.get('steps', '')} {r.get('mism', '')} {r.get('err', '')}")
    print("ALL OK" if allok else "NOT OK")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gen")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--window", type=int, default=128)
    g.add_argument("--prompt", type=int, default=24)
    g.add_argument("--steps", type=int, default=160)
    g.add_argument("--seed", type=int, default=1)
    r = sp.add_parser("run")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--backend", choices=["rom", "hbm"], required=True)
    r.add_argument("--mutant")
    r.add_argument("--spec-f", action="store_true")
    r.add_argument("--sim", default="verilator")
    c = sp.add_parser("campaign")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--record", type=Path)
    c.add_argument("--sim", default="verilator")
    c.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "gen":
        print(json.dumps(gen(a.out, a.window, a.prompt, a.steps, a.seed), indent=1))
    elif a.cmd == "run":
        print(json.dumps(run(a.out, a.backend, a.mutant, a.sim, a.spec_f), indent=1))
    else:
        campaign(a.out, a.sim, a.record, a.jobs)


if __name__ == "__main__":
    main()
