#!/usr/bin/env python3
"""RTL campaign for the DeepSeek-V4.1 ROM array's communication operators.

Engines under rtl/rom/collectives/ (record format: ot_rom_coll_pkg.sv):

* ot_rom_moe_dispatch     -- MoE expert-parallel dispatch (multicast or
                             destination-major unicast, placement-table ROM,
                             golden sum-order ranks stamped in flight);
* ot_rom_moe_expert_port  -- the expert package's receive filter and return
                             header insertion;
* ot_rom_moe_combine      -- reorder buffer and in-order binary32 sum, bit
                             exact against tools/hdc_golden_v41 whatever the
                             arrival order;
* ot_rom_mcast_node       -- KV-source row multicast along the package chain
                             (and all-gather on a ring);
* ot_rom_argmax_reduce    -- the vocabulary-split lm_head's carried argmax.

Benches (Verilator, rtl/test/):

1. tb_rom_moe_collectives: five packages joined by rtl/rom/ot_rom_pkg_link.sv
   (home + four expert packages), the home's activation quantiser
   (rtl/hdc/v41/ot_hdc_actquant.sv) in front of the dispatch.  Traces: REAL
   reduced-V4.1 MoE instances captured from tools/hdc_golden_v41.Model (the
   oracle workload's prompt and generated tokens, every layer; the expert
   outputs the golden's own expert(), the MoE output its own moe()) and random
   ones (random routes, random BF16 expert outputs with zeros, -0, subnormals,
   cancellations and large magnitudes, expected sums by hdc_golden.add in the
   golden's order).  Cases: multicast and unicast dispatch, lone-token latency
   against the link latency law, sustained throughput, and stress (random
   back-pressure on every link endpoint, random expert latency, small credits).
2. tb_rom_kv_argmax: an 8-package chain of ot_rom_mcast_node joined by links
   carrying the golden's real compressed-KV rows, index keys and selections
   from the four KV sources to their consumer layers' packages; a ring
   all-gather; and the carried argmax across 8 vocabulary slices on the
   golden's real logits plus random logits with ties.

Writes results/rtl/rom_collectives_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("OPENTALLAS_BUILD", str(ROOT / "build"))
import hdc_golden_v41 as G  # noqa: E402
from hdc_golden import F, add, bits, fold, from_bits, to_bf16  # noqa: E402

OUT = ROOT / "results/rtl/rom_collectives_campaign.json"
COLL = ROOT / "rtl/rom/collectives"
PKG = COLL / "ot_rom_coll_pkg.sv"
SKID = COLL / "ot_rom_coll_skid.sv"
DISPATCH = COLL / "ot_rom_moe_dispatch.sv"
PORT = COLL / "ot_rom_moe_expert_port.sv"
COMBINE = COLL / "ot_rom_moe_combine.sv"
MCAST = COLL / "ot_rom_mcast_node.sv"
ARGMAX = COLL / "ot_rom_argmax_reduce.sv"
ENGINES = [PKG, SKID, DISPATCH, PORT, COMBINE, MCAST, ARGMAX]
LINK = ROOT / "rtl/rom/ot_rom_pkg_link.sv"
ADD = ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"
AQ = [ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv", ROOT / "rtl/hdc/ot_hdc_fpu.sv", ROOT / "rtl/hdc/ot_hdc_delay.sv",
      ROOT / "rtl/hdc/ot_hdc_fp32_mul_pipe.sv"]
TB_MOE = ROOT / "rtl/test/tb_rom_moe_collectives.sv"
TB_KV = ROOT / "rtl/test/tb_rom_kv_argmax.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_golden_v41.py", Path(__file__)]
MOE_SOURCES = [PKG, SKID, DISPATCH, PORT, COMBINE, LINK, ADD, *AQ, TB_MOE]
KV_SOURCES = [PKG, SKID, MCAST, ARGMAX, LINK, TB_KV]
ROUTER = ROOT / "rtl/rom/ot_rom_fabric_router.sv"
TB_AR = ROOT / "rtl/test/tb_rom_tensor_allreduce.sv"
AR_SOURCES = [PKG, ADD, COMBINE, ROUTER, TB_AR]
VL_FLAGS = ("--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
            "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN", "-Wno-COMBDLY")
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-IMPORTSTAR")

# reduced V4.1 shapes and the bench's array
DIM, NB, N_EXP, K_EXP, NR = 160, 5, 12, 6, 7
FLIT_BITS, ACT_FLITS, VEC_FLITS = 512, 3, 5
NPKG = 5
PLACE = [1 + (e % 4) for e in range(N_EXP)] + [0]          # the shared expert on the home package
CLOCK_HZ = 1e9
# the link as instantiated by the benches: ot_rom_pkg_link TX 2, RX 2, registered output
LINK_TX, LINK_RX, LINK_OUT = 2, 2, 1


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hex(v: int, bits_: int) -> str:
    return f"{v:0{bits_ // 4}x}"


def _pack(fields, width):
    acc = 0
    for i, f in enumerate(fields):
        acc |= (int(f) & ((1 << width) - 1)) << (width * i)
    return acc


# -- the E4M3 code of a quant_fp8 value ------------------------------------------------------
_E4M3_CODE = {}
for _c in range(256):
    if (_c & 0x7F) == 0x7F:
        continue
    _E4M3_CODE[(float(abs(G.E4M3[_c])), _c >> 7)] = _c


def act_payload(x):
    """quant_fp8(x) as the dispatch carries it: 32 E4M3 codes per block (x * 2^-e,
    signed zeros kept, as ot_hdc_actquant encodes), then the exponents."""
    q, e = G.quant_fp8(np.asarray(x, dtype=F))
    codes = [_E4M3_CODE[(abs(float(v)), int(np.signbit(v)))] for v in q]
    xb = G.bits(np.asarray(x, dtype=F))
    # -0 input quantises to +0 (np.sign(-0.0) = +0 in the golden)
    codes = [0 if (int(b) == 0x80000000) else c for b, c in zip(xb, codes)]
    assert all(-128 <= int(v) <= 127 for v in e)
    by = codes + [int(v) & 0xFF for v in e]
    by += [0] * (ACT_FLITS * FLIT_BITS // 8 - len(by))
    return [_pack(by[64 * f:64 * (f + 1)], 8) for f in range(ACT_FLITS)], q, e


# -- traces ------------------------------------------------------------------------------------
def capture_real(positions: int):
    """Run the golden over the oracle workload (prompt, then its expected tokens),
    recording every layer's MoE instance, the logits, the KV sources' compressed rows
    and index keys, and the index sources' selections."""
    m = G.Model()
    prompt, expected = G.prompt_and_expected()
    tokens = (list(prompt) + list(expected))[:positions]
    moe, kv, sel = [], [], []
    orig_moe, orig_indexer = m.moe, m.indexer
    cur = {"pos": 0}

    def moe_capture(L, x, trace):
        y = orig_moe(L, x, trace)
        scores = G.sqrt(G.softplus(G.matvec_fp32(m.lw(L, "ffn.gate.weight"), x)))
        chosen = G.topk_lowest_index(add(scores, m.lw(L, "ffn.gate.bias")), m.k_exp)
        order = [int(i) for i in chosen]                       # the router's own emission order
        ids = sorted(order)
        total = G.seqsum([scores[i] for i in ids])
        den = add(total, F(1e-20))
        wgt = {i: G.mul(G.div(scores[i], den), m.route_scale) for i in ids}
        outs = [m.expert(f"layers.{L}.ffn.experts.{i}.", x, wgt[i]) for i in ids]
        outs.append(m.expert(f"layers.{L}.ffn.shared_experts.", x))
        acc = np.zeros(m.dim, dtype=F)
        for o in outs:
            acc = add(acc, o)
        assert np.array_equal(bits(to_bf16(acc)), bits(y)), "MoE recomputation differs from the golden"
        moe.append({"pos": cur["pos"], "layer": L, "x": np.asarray(x, dtype=F), "order": order, "ids": ids,
                    "wgt": [np.float32(wgt[i]) for i in ids], "outs": outs, "y": y})
        return y

    def indexer_capture(L, x, qr, pos, state, trace):
        s = orig_indexer(L, x, qr, pos, state, trace)
        sel.append({"pos": pos, "layer": L, "sel": [int(v) for v in s]})
        return s

    m.moe, m.indexer = moe_capture, indexer_capture
    state = m.new_state()
    logits = []
    seen = {s: 0 for s in m.kv_src}
    for p, t in enumerate(tokens):
        cur["pos"] = p
        logits.append(m.decode_token(t, p, state))
        for s in m.kv_src:
            while seen[s] < len(state["ckv"][s]):
                i = seen[s]
                kv.append({"pos": p, "layer": s, "row": np.asarray(state["ckv"][s][i], dtype=F),
                           "key": np.asarray(state["ik"][s][i], dtype=F)})
                seen[s] += 1
    return {"tokens": tokens, "moe": moe, "logits": logits, "kv": kv, "sel": sel,
            "kv_of": {int(k): int(v) for k, v in m.kv_of.items()},
            "idx_of": {int(k): int(v) for k, v in m.idx_of.items()},
            "kv_src": list(m.kv_src), "idx_src": list(m.idx_src)}


def _rand_bf16(rng, n, kind):
    """n BF16 values (as float32) of a flavour: normal magnitudes, extremes, zeros, subnormals."""
    if kind == "normal":
        e = rng.integers(110, 140, n)
    elif kind == "wide":
        e = rng.integers(1, 251, n)
    else:
        e = rng.integers(0, 3, n)                                  # subnormal and tiny
    m = rng.integers(0, 128, n)
    s = rng.integers(0, 2, n)
    b = (s << 15) | (e << 7) | m
    z = rng.random(n)
    b = np.where(z < 0.03, 0, np.where(z < 0.05, 0x8000, b))
    return from_bits((b.astype(np.uint32) << 16))


def random_moe(rng, n):
    out = []
    kinds = ["normal", "normal", "wide", "tiny"]
    for t in range(n):
        order = [int(v) for v in rng.permutation(N_EXP)[:K_EXP]]
        ids = sorted(order)
        sc = rng.random(K_EXP).astype(F) + F(0.01)
        den = add(G.seqsum([sc[i] for i in range(K_EXP)]), F(1e-20))
        wgt = [np.float32(G.mul(G.div(sc[i], den), F(1.5))) for i in range(K_EXP)]
        x = to_bf16((rng.standard_normal(DIM) * np.exp2(rng.integers(-12, 6))).astype(F))
        if t % 7 == 3:
            x[rng.integers(0, DIM, 8)] = F(0)
        kind = kinds[t % 4]
        outs = [_rand_bf16(rng, DIM, kind) for _ in range(NR)]
        if t % 5 == 1:                                             # exact cancellations in the chain
            r = int(rng.integers(0, NR - 1))
            outs[r + 1] = from_bits(bits(outs[r]) ^ np.uint32(0x80000000))
        if t % 11 == 2:                                            # one huge term swamps the rest
            outs[int(rng.integers(0, NR))] = _rand_bf16(rng, DIM, "wide")
        acc = np.zeros(DIM, dtype=F)
        for o in outs:
            acc = add(acc, o)
        out.append({"pos": -1, "layer": -1, "x": x, "order": order, "ids": ids, "wgt": wgt, "outs": outs,
                    "y": to_bf16(acc)})
    return out


def _bf16_flits(v):
    h = (bits(np.asarray(v, dtype=F)) >> 16).astype(np.int64)
    return [_pack(h[32 * c:32 * (c + 1)], 16) for c in range(VEC_FLITS)]


def write_moe_vectors(d: Path, insts):
    d.mkdir(parents=True, exist_ok=True)
    fx, fd, fa, fo, fm, fy = ([] for _ in range(6))
    for inst in insts:
        x = np.asarray(inst["x"], dtype=F)
        xb = bits(x).astype(np.int64)
        for b in range(NB):
            fx.append(_hex(_pack(xb[32 * b:32 * (b + 1)], 32), 1024))
        desc = (3 << 16) | (((1 << K_EXP) - 1) << 64)
        wmap = dict(zip(inst["ids"], inst["wgt"]))
        for i, e in enumerate(inst["order"]):                     # router order, not sorted
            w = int(bits(np.float32(wmap[e])))
            desc |= (w | (e << 32)) << (80 + 48 * i)
        fd.append(_hex(desc, FLIT_BITS))
        flits, _, _ = act_payload(x)
        fa += [_hex(f, FLIT_BITS) for f in flits]
        for r in range(NR):
            fo += [_hex(f, FLIT_BITS) for f in _bf16_flits(inst["outs"][r])]
            if r < K_EXP:
                fm.append(_hex(int(bits(np.float32(inst["wgt"][r]))) | (inst["ids"][r] << 32), 64))
            else:
                fm.append(_hex(N_EXP << 32, 64))
        fy += [_hex(f, FLIT_BITS) for f in _bf16_flits(inst["y"])]
    for name, lines in (("x", fx), ("desc", fd), ("act", fa), ("out", fo), ("meta", fm), ("moe", fy)):
        (d / f"{name}.mem").write_text("\n".join(lines) + "\n")
    return len(insts)


# -- simulation ------------------------------------------------------------------------------------
def build(obj: Path, top: str, sources, params=()):
    cflags = f"-DVTOP=V{top} -O1"
    cmd = ["verilator", *VL_FLAGS, "--top-module", top, "-Mdir", str(obj), *[f"-G{p}" for p in params],
           *map(str, sources), str(HARNESS), "-CFLAGS", cflags]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-4000:])
    return obj / f"V{top}"


RE_MOE = re.compile(r"MOE tokens=(\d+) done=(\d+) chunks=(\d+) errors=(\d+) order_errors=(\d+) exp_errors=(\d+) "
                    r"place_errors=(\d+) aq_errors=(\d+) aq_faults=(\d+) faults=(\d)(\d)(\d) jobs=(\d+) jobs_full=(\d+)")
RE_MOESTAT = re.compile(r"MOESTAT (.*)")
RE_MOEFLITS = re.compile(r"MOEFLITS (.*)")


def _kv(text):
    return {k: int(v) for k, v in (t.split("=") for t in text.split())}


def run_moe(exe: Path, vec: Path, n, **plus):
    args = [str(exe), f"+VEC={vec}", f"+N={n}"] + [f"+{k.upper()}={v}" for k, v in plus.items()]
    r = subprocess.run(args, capture_output=True, text=True, timeout=7200)
    m = RE_MOE.search(r.stdout)
    if not m:
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-2000:])
    g = list(map(int, m.groups()))
    res = {"tokens": g[0], "done": g[1], "chunks_checked": g[2], "moe_mismatches": g[3], "chunk_order_errors": g[4],
           "expert_side_errors": g[5], "placement_errors": g[6], "actquant_mismatches": g[7],
           "actquant_faults": g[8], "dispatch_fault": g[9], "combine_fault": g[10], "port_fault": g[11],
           "expert_jobs": g[12], "job_table_overflows": g[13]}
    res.update(_kv(RE_MOESTAT.search(r.stdout).group(1)))
    res.update(_kv(RE_MOEFLITS.search(r.stdout).group(1)))
    res.update(_kv(re.search(r"MOEDSP (.*)", r.stdout).group(1)))
    res["pass"] = (res["done"] == n and res["chunks_checked"] == n * VEC_FLITS and
                   all(res[k] == 0 for k in ("moe_mismatches", "chunk_order_errors", "expert_side_errors",
                                             "placement_errors", "actquant_mismatches", "actquant_faults",
                                             "dispatch_fault", "combine_fault", "port_fault", "job_table_overflows",
                                             "dest_errors")))
    res["plusargs"] = plus
    res["mismatch_lines"] = [ln for ln in r.stdout.splitlines() if ln.startswith("MISMATCH")][:5]
    return res


# -- KV multicast / all-gather and the carried argmax ---------------------------------------------
KV_NP, LAYERS_PER_PKG, VOCAB, LANES_AM = 8, 5, 4040, 16
SLICE = VOCAB // KV_NP


def pkg_of(layer):
    return layer // LAYERS_PER_PKG


def kv_plan(real):
    """The chain's multicast groups from the golden's own source maps: KV source s ->
    the packages of the layers that read s's compressed KV (kv_of), index source s ->
    the packages of the layers that read s's selection (idx_of); the source's own
    package excluded (it reads locally)."""
    kv_cons = {s: sorted({pkg_of(L) for L, v in real["kv_of"].items() if v == s} - {pkg_of(s)})
               for s in real["kv_src"]}
    idx_cons = {s: sorted({pkg_of(L) for L, v in real["idx_of"].items() if v == s} - {pkg_of(s)})
                for s in real["idx_src"]}
    cons = [0] * KV_NP
    for s, ps in kv_cons.items():
        assert cons[pkg_of(s)] == 0, "one KV source per package"
        cons[pkg_of(s)] = sum(1 << q for q in ps)
    return kv_cons, idx_cons, cons


def kv_records(real, rng, ring: bool, n_random: int):
    """Records in global injection order: src package, expected destination set, the
    header's own mask (0: the node's CONSUMERS table applies), payload flits."""
    recs = []
    if not ring:
        kv_cons, idx_cons, cons = kv_plan(real)
        events = []
        for e in real["kv"]:
            events.append((e["pos"], e["layer"], 0, e))
        for e in real["sel"]:
            if idx_cons.get(e["layer"]):
                events.append((e["pos"], e["layer"], 1, e))
        for pos, layer, kind, e in sorted(events, key=lambda t: (t[0], t[1], t[2])):
            src = pkg_of(layer)
            if kind == 0:
                mask = sum(1 << q for q in kv_cons[layer])
                row = (bits(e["row"]) >> 16).astype(np.int64)
                key = (bits(e["key"]) >> 16).astype(np.int64)
                recs.append({"src": src, "mask": mask, "hdr_mask": 0, "layer": layer, "pos": pos, "sel": [],
                             "payload": [_pack(row, 16), _pack(key, 16)], "kind": "kv_row"})
            else:
                mask = sum(1 << q for q in idx_cons[layer])
                recs.append({"src": src, "mask": mask, "hdr_mask": mask, "layer": layer, "pos": pos,
                             "sel": e["sel"][:16], "payload": [], "kind": "selection"})
        # random extra traffic: any package to a random set of downstream packages, 1..4 flits
        for _ in range(n_random):
            src = int(rng.integers(0, KV_NP - 1))
            down = [q for q in range(src + 1, KV_NP) if rng.random() < 0.5] or [KV_NP - 1]
            mask = sum(1 << q for q in down)
            recs.append({"src": src, "mask": mask, "hdr_mask": mask, "layer": 255, "pos": 0, "sel": [],
                         "payload": [int.from_bytes(rng.bytes(64), "little") for _ in range(int(rng.integers(0, 4)))],
                         "kind": "random"})
    else:
        cons = [0] * KV_NP
        rows = real["kv"]
        for i in range(n_random):
            src = i % KV_NP
            e = rows[i % len(rows)]
            mask = ((1 << KV_NP) - 1) & ~(1 << src)
            recs.append({"src": src, "mask": mask, "hdr_mask": mask, "layer": e["layer"], "pos": e["pos"], "sel": [],
                         "payload": [_pack((bits(e["row"]) >> 16).astype(np.int64), 16),
                                     _pack((bits(e["key"]) >> 16).astype(np.int64), 16)], "kind": "all_gather"})
    return recs, cons


def write_kv_vectors(d: Path, recs):
    d.mkdir(parents=True, exist_ok=True)
    per = [[] for _ in range(KV_NP)]
    meta = {"rmask": [], "rsrc": [], "rlen": [], "roff": []}
    for rid, r in enumerate(recs):
        hdr = ((5 << 16) | (r["src"] << 8) | (len(r["payload"]) << 24) | (r["hdr_mask"] << 48)
               | ((r["layer"] & 0xFF) << 72) | (r["pos"] << 80) | (rid << 112))
        for i, s in enumerate(r["sel"]):
            hdr |= (s & 0xFFFF) << (128 + 16 * i)
        flits = [hdr] + r["payload"]
        meta["rmask"].append(r["mask"])
        meta["rsrc"].append(r["src"])
        meta["rlen"].append(len(flits))
        meta["roff"].append(len(per[r["src"]]))
        for i, f in enumerate(flits):
            per[r["src"]].append(((1 if i == len(flits) - 1 else 0) << FLIT_BITS) | f)
    for p in range(KV_NP):
        (d / f"inj{p}.mem").write_text("".join(f"{v:0129x}\n" for v in per[p]) or "0\n")
    (d / "ninj.mem").write_text("".join(f"{len(per[p]):08x}\n" for p in range(KV_NP)))
    (d / "nrec.mem").write_text(f"{len(recs):08x}\n")
    (d / "rmask.mem").write_text("".join(f"{v:04x}\n" for v in meta["rmask"]))
    (d / "rsrc.mem").write_text("".join(f"{v:x}\n" for v in meta["rsrc"]))
    (d / "rlen.mem").write_text("".join(f"{v:08x}\n" for v in meta["rlen"]))
    (d / "roff.mem").write_text("".join(f"{v:08x}\n" for v in meta["roff"]))
    assert max(len(x) for x in per) <= 4096 and len(recs) <= 4096
    kinds = {}
    for r in recs:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    return {"records": len(recs), "records_by_kind": kinds,
            "deliveries": sum(bin(m).count("1") for m in meta["rmask"]),
            "flits_injected": sum(len(x) for x in per)}


def random_logits(rng, n):
    out = []
    for t in range(n):
        v = (rng.standard_normal(VOCAB) * np.exp2(rng.integers(-3, 4))).astype(F)
        kind = t % 4
        if kind == 1:                                   # the maximum repeated at other ids, across slices
            i = int(rng.integers(0, VOCAB))
            top = F(np.abs(v).max() + 1)
            v[i] = top
            for j in rng.integers(0, VOCAB, int(rng.integers(1, 4))):
                v[int(j)] = top
        elif kind == 2:                                 # every logit negative, the maximum a signed zero
            v = (-np.abs(v) - F(1)).astype(F)
            zs = sorted(int(j) for j in rng.choice(VOCAB, 3, replace=False))
            v[zs[0]] = F(-0.0)
            v[zs[1]] = F(0.0)
            v[zs[2]] = F(-0.0)
        elif kind == 3:                                 # a tie across a slice boundary
            b = SLICE * int(rng.integers(1, KV_NP))
            top = F(np.abs(v).max() + 2)
            v[b - 1] = top
            v[b] = top
        out.append(v)
    return out


def write_argmax_vectors(d: Path, logits):
    d.mkdir(parents=True, exist_ok=True)
    beats = -(-SLICE // LANES_AM)
    lines, am = [], []
    for v in logits:
        v = np.asarray(v, dtype=F)
        vb = bits(v).astype(np.int64)
        for g in range(KV_NP):
            for b in range(beats):
                lo = g * SLICE + b * LANES_AM
                lanes = [int(vb[lo + i]) if b * LANES_AM + i < SLICE else 0 for i in range(LANES_AM)]
                lines.append(_hex(_pack(lanes, 32), FLIT_BITS))
        i = int(np.argmax(v))                               # the golden's rule: lowest id among the maxima
        am.append(_hex((i << 32) | int(vb[i]), 64))
    (d / "lg.mem").write_text("\n".join(lines) + "\n")
    (d / "am.mem").write_text("\n".join(am) + "\n")
    return len(logits)


RE_KV = re.compile(r"KV records=(\d+) deliveries=(\d+) expected=(\d+) errors=(\d+) leaked=(\d+) injected=(\d+) "
                   r"forwarded=(\d+) credit_stalls=(\d+) done_cycle=(\d+)")
RE_KVHOP = re.compile(r"KVHOP hops=(\d+) lat_min=(\d+) lat_max=(\d+)")
RE_AM = re.compile(r"ARGMAX tokens=(\d+) got=(\d+) errors=(\d+) faults=(\d+) first=(\d+) last=(\d+) q1=(\d+) "
                   r"q3=(\d+)")


def run_kv(exe: Path, vec: Path, na: int, **plus):
    args = [str(exe), f"+VEC={vec}", f"+NA={na}"] + [f"+{k.upper()}={v}" for k, v in plus.items()]
    r = subprocess.run(args, capture_output=True, text=True, timeout=7200)
    m, a = RE_KV.search(r.stdout), RE_AM.search(r.stdout)
    if not (m and a):
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-2000:])
    kv = dict(zip(("records", "deliveries", "expected_deliveries", "errors", "leaked", "injected", "forwarded",
                   "credit_stalls", "done_cycle"), map(int, m.groups())))
    am = dict(zip(("tokens", "got", "errors", "fault", "first", "last", "q1", "q3"), map(int, a.groups())))
    kv["latency_by_hops"] = {int(h): {"min_cycles": int(lo), "max_cycles": int(hi)}
                             for h, lo, hi in RE_KVHOP.findall(r.stdout) if int(lo) < (1 << 30)}
    kv["pass"] = kv["deliveries"] == kv["expected_deliveries"] and kv["errors"] == 0 and kv["leaked"] == 0
    am["pass"] = am["got"] == na and am["errors"] == 0 and am["fault"] == 0
    return {"kv": kv, "argmax": am, "plusargs": plus,
            "mismatch_lines": [ln for ln in r.stdout.splitlines() if "MISMATCH" in ln][:5]}


# -- the tensor group's one-shot fixed-order all-reduce -------------------------------------------
N_ALLREDUCE = 512
AR_DIES, AR_FLITS = 4, 5                          # 4 dies of a package; 80 binary32 per partial


def write_allreduce_vectors(d: Path, rng, n):
    """Random binary32 partials (every binade, zeros, subnormals, exact cancellations) and their
    sum in rank order, hdc_golden.fold -- the one-shot rule of results/roofline/critical_path
    ("every die sums all partials in rank order")."""
    d.mkdir(parents=True, exist_ok=True)
    width = AR_FLITS * 16
    parts, sums = [], []
    for t in range(n):
        e = rng.integers(1, 250 if t % 3 else 20, (AR_DIES, width))
        b = (rng.integers(0, 2, (AR_DIES, width)) << 31) | (e << 23) | rng.integers(0, 1 << 23, (AR_DIES, width))
        z = rng.random((AR_DIES, width))
        b = np.where(z < 0.03, 0, np.where(z < 0.05, 0x80000000, b)).astype(np.uint32)
        p = from_bits(b)
        if t % 4 == 1:
            p[1] = from_bits(bits(p[0]) ^ np.uint32(0x80000000))
        # the engine starts from +0: add(+0, p0) is p0 except that -0 becomes +0, which is
        # hdc_golden.fold's ((p0 + p1) + p2) + p3 whenever the sum is not an all-zero column
        acc = add(np.zeros(width, dtype=F), fold(list(p)))
        if not np.all(np.isfinite(acc)):
            p[:, ~np.isfinite(acc)] = F(1.0)
            acc = add(np.zeros(width, dtype=F), fold(list(p)))
        for r in range(AR_DIES):
            pb = bits(p[r]).astype(np.int64)
            parts += [_hex(_pack(pb[16 * c:16 * (c + 1)], 32), FLIT_BITS) for c in range(AR_FLITS)]
        ab = bits(acc).astype(np.int64)
        sums += [_hex(_pack(ab[16 * c:16 * (c + 1)], 32), FLIT_BITS) for c in range(AR_FLITS)]
    (d / "ar_part.mem").write_text("\n".join(parts) + "\n")
    (d / "ar_sum.mem").write_text("\n".join(sums) + "\n")
    return n


RE_AR = re.compile(r"ALLREDUCE reductions=(\d+) replicas=(\d+) errors=(\d+) faults=(\d+) drops=(\d+) "
                   r"overflow=(\d+) cycles=(\d+)")


def run_allreduce(exe: Path, vec: Path, n: int, **plus):
    args = [str(exe), f"+VEC={vec}", f"+N={n}"] + [f"+{k.upper()}={v}" for k, v in plus.items()]
    r = subprocess.run(args, capture_output=True, text=True, timeout=7200)
    m = RE_AR.search(r.stdout)
    if not m:
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-2000:])
    res = dict(zip(("reductions", "replicas_checked", "errors", "fault", "router_drops", "router_overflow",
                    "cycles"), map(int, m.groups())))
    res["pass"] = (res["replicas_checked"] == AR_DIES * n and all(res[k] == 0 for k in
                   ("errors", "fault", "router_drops", "router_overflow")))
    res["cycles_per_reduction"] = round(res["cycles"] / n, 3)
    res["plusargs"] = plus
    return res


# -- the campaign ------------------------------------------------------------------------------------
PHYS = ROOT / "results/physical_abi3/asap7/rom/collectives"
PHYS_TOPS = ("ot_rom_moe_dispatch", "ot_rom_moe_dispatch_unicast", "ot_rom_moe_expert_port", "ot_rom_moe_combine",
             "ot_rom_mcast_node", "ot_rom_argmax_reduce")
REAL_POSITIONS = 16            # the oracle workload's 8 prompt tokens and its first 8 generated tokens
N_RANDOM_MOE = 2048
N_RANDOM_KV = 400
N_RING = 320
N_RANDOM_LOGITS = 112
LINK_CH = 60                   # ot_rom_pkg_link CHANNEL_CYCLES in both benches
HOP = LINK_TX + LINK_CH + LINK_RX + LINK_OUT     # a link's first-flit latency law, cycles
MOE_BUILDS = {                 # name: bench parameters
    "multicast": ("MCAST=1", "TAGS=8"),
    "unicast": ("MCAST=0", "TAGS=8"),
    "multicast_credits8": ("MCAST=1", "TAGS=8", "CREDITS=8"),
    "multicast_tags4": ("MCAST=1", "TAGS=4"),
    "multicast_tags2": ("MCAST=1", "TAGS=2"),
}
STRESS = {"bp": 30, "elat": 60, "gap": 20}
MOE_CASES = [                  # (build, trace, label, plusargs)
    ("multicast", "real", "real_sustained", {}),
    ("multicast", "real", "real_lone_token", {"serial": 1}),
    ("multicast", "real", "real_stress", STRESS),
    ("multicast", "random", "random_sustained", {}),
    ("multicast", "random", "random_stress", {**STRESS, "seed": 5}),
    ("unicast", "real", "real_sustained", {}),
    ("unicast", "real", "real_lone_token", {"serial": 1}),
    ("unicast", "random", "random_stress", {**STRESS, "seed": 9}),
    ("multicast_credits8", "random", "random_stress_credits8", {**STRESS, "seed": 13}),
    ("multicast_tags4", "random", "random_sustained", {}),
    ("multicast_tags2", "random", "random_sustained", {}),
]


def _derive_moe(r, n):
    half = n // 2
    r["steady_cycles_per_token"] = round((r["q3"] - r["q1"]) / max(1, (3 * n) // 4 - n // 4), 3)
    r["mean_latency_cycles"] = round(r["lat_sum"] / max(1, r["done"]), 2)
    r["dispatch_flits_per_token"] = round(r["dsp_flits"] / n, 3)
    r["dispatch_records_per_token"] = round(r["dsp_records"] / n, 3)
    r["return_flits_per_token"] = round(r["ret_flits"] / n, 3)
    del half
    return r


def run_campaign(scratch: Path, jobs: int = 5) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    rng = np.random.default_rng(20260924)
    real = capture_real(REAL_POSITIONS)
    rand = random_moe(rng, N_RANDOM_MOE)
    vec = {"real": scratch / "moe_real", "random": scratch / "moe_random"}
    ntok = {"real": write_moe_vectors(vec["real"], real["moe"]), "random": write_moe_vectors(vec["random"], rand)}
    recs, cons = kv_records(real, rng, False, N_RANDOM_KV)
    recs_real = [r for r in recs if r["kind"] != "random"]
    ring_recs, _ = kv_records(real, rng, True, N_RING)
    logits = list(real["logits"]) + random_logits(rng, N_RANDOM_LOGITS)
    kvvec = {"chain_real": scratch / "kv_real", "chain_mixed": scratch / "kv_mixed", "ring": scratch / "kv_ring"}
    kvinfo = {"chain_real": write_kv_vectors(kvvec["chain_real"], recs_real),
              "chain_mixed": write_kv_vectors(kvvec["chain_mixed"], recs),
              "ring": write_kv_vectors(kvvec["ring"], ring_recs)}
    for d in kvvec.values():
        write_argmax_vectors(d, logits)
    consv = sum(c << (16 * i) for i, c in enumerate(cons))
    ar_n = write_allreduce_vectors(scratch / "allreduce", rng, N_ALLREDUCE)
    kv_builds = {"chain": ("RING=0", f"CONS=128'h{consv:032x}"), "ring": ("RING=1",)}

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = {n: pool.submit(build, scratch / f"obj_{n}", "tb_rom_moe_collectives", MOE_SOURCES, p)
                for n, p in MOE_BUILDS.items()}
        futs.update({f"kv_{n}": pool.submit(build, scratch / f"obj_kv_{n}", "tb_rom_kv_argmax", KV_SOURCES, p)
                     for n, p in kv_builds.items()})
        futs["allreduce"] = pool.submit(build, scratch / "obj_allreduce", "tb_rom_tensor_allreduce", AR_SOURCES, ())
        exe = {n: f.result() for n, f in futs.items()}
        ar_futs = [(plus, pool.submit(run_allreduce, exe["allreduce"], scratch / "allreduce", ar_n, **plus))
                   for plus in ({}, {"gap": 40, "seed": 21})]
        moe_futs = [(b, t, lab, plus, pool.submit(run_moe, exe[b], vec[t], ntok[t], **plus))
                    for b, t, lab, plus in MOE_CASES]
        kv_futs = [("chain", "chain_real", {}), ("chain", "chain_mixed", {}), ("chain", "chain_mixed", {"bp": 30}),
                   ("ring", "ring", {}), ("ring", "ring", {"bp": 30, "seed": 3})]
        kv_futs = [(b, v, plus, pool.submit(run_kv, exe[f"kv_{b}"], kvvec[v], len(logits), **plus))
                   for b, v, plus in kv_futs]
        moe = []
        for b, t, lab, plus, f in moe_futs:
            r = _derive_moe(f.result(), ntok[t])
            moe.append({"build": b, "parameters": list(MOE_BUILDS[b]), "trace": t, "label": lab, **r})
        kv = []
        for b, v, plus, f in kv_futs:
            r = f.result()
            kv.append({"build": b, "vectors": v, "parameters": list(kv_builds[b]), **r})
        allreduce = [f.result() for plus, f in ar_futs]

    lint = {}
    for top, src in (("ot_rom_moe_dispatch", [PKG, SKID, DISPATCH]), ("ot_rom_moe_expert_port", [PKG, SKID, PORT]),
                     ("ot_rom_moe_combine", [PKG, ADD, COMBINE]), ("ot_rom_mcast_node", [PKG, SKID, MCAST]),
                     ("ot_rom_argmax_reduce", [PKG, SKID, ARGMAX])):
        p = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", top, *map(str, src)],
                           capture_output=True, text=True)
        lint[top] = {"returncode": p.returncode, "messages": p.stderr.strip().splitlines()[:10]}

    def case(build, label):
        return next(c for c in moe if c["build"] == build and c["label"] == label)

    lone = case("multicast", "real_lone_token")
    lone_u = case("unicast", "real_lone_token")
    sus = case("multicast", "real_sustained")
    sus_u = case("unicast", "real_sustained")
    rand_s = case("multicast", "random_sustained")
    ingest_bound = NR * (1 + VEC_FLITS)
    chain_real = next(k for k in kv if k["vectors"] == "chain_real")
    hops = chain_real["kv"]["latency_by_hops"]
    per_hop = sorted(hops)
    node_overhead = {h: hops[h]["min_cycles"] - h * HOP for h in per_hop}
    am = chain_real["argmax"]
    ok = (all(c["pass"] for c in moe) and all(k["kv"]["pass"] and k["argmax"]["pass"] for k in kv)
          and all(c["pass"] for c in allreduce)
          and all(v["returncode"] == 0 for v in lint.values()))
    record = {
        "schema": "opentallas.rom-collectives-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": (
            "Functional, cycle-accurate RTL of the communication engines (dispatch, expert port, combine, "
            "KV multicast node, carried argmax) between ot_rom_pkg_link instances under Verilator.  The links' "
            "CHANNEL_CYCLES is a delay-line stand-in for the PHY; the fabric between packages is the benches' own "
            "multicast demultiplexer and round-robin merge, not the RTL router; the expert COMPUTE is a behavioural "
            "model returning the golden's expert outputs (its inputs are checked against the golden).  Bit-exactness "
            "is of the MoE combine against tools/hdc_golden_v41 and of every delivered byte."),
        "parameters": {
            "model": "DeepSeek-V4.1-Flash reduced v2 (dim 160, 12 routed experts, top-6, 1 shared expert)",
            "flit_bits": FLIT_BITS, "activation_flits": ACT_FLITS, "expert_output_flits": VEC_FLITS,
            "ranks_per_token": NR, "packages_moe_bench": NPKG,
            "placement": {"routed_expert_package": PLACE[:N_EXP], "shared_expert_package": PLACE[N_EXP]},
            "link": {"tx_stages": LINK_TX, "channel_cycles": LINK_CH, "rx_stages": LINK_RX, "output_stage": LINK_OUT,
                     "first_flit_latency_cycles": HOP, "credits": 128},
            "kv_chain_packages": KV_NP, "layers_per_package": LAYERS_PER_PKG,
            "kv_consumer_masks": [f"0x{c:04x}" for c in cons],
            "argmax_slices": KV_NP, "argmax_slice_logits": SLICE, "argmax_lanes": LANES_AM, "vocab": VOCAB,
            "clock_hz": CLOCK_HZ},
        "numerics": {
            "combine_order": ("per element: +0, then the routed experts in ascending id (rank 0..5), then the shared "
                              "expert, each a binary32 add (rtl/proto/ot_fp32_add_rne_pipe.sv), then to_bf16 -- "
                              "tools/hdc_golden_v41.Model.moe exactly; arrival order never enters the sum"),
            "dispatch_payload": "quant_fp8 of the MoE input: E4M3 codes per 32-element block + UE8M0 exponents, "
                                "produced by rtl/hdc/v41/ot_hdc_actquant.sv in the bench and checked against the golden",
            "argmax_rule": "strictly greater replaces (lowest id on ties; -0 equals +0), = np.argmax",
            "tensor_group_allreduce": (
                "results/roofline/critical_path's one-shot rule, every die sums all partials in die-rank order "
                "from +0: ot_rom_moe_combine with IN_W=32, NRANK=4, bit-identical on all four replicas.  It is "
                "bit-exact to tools/hdc_golden_v41 only where the golden sums in that order: linear_q and moe "
                "accumulate sequentially over K blocks and over experts, so a contraction split across dies needs "
                "the golden to adopt the split (as hdc_golden.matvec's K-split does for BF16), while the MoE "
                "combine stays exact by exchanging whole expert outputs in id order (7 BF16 vectors = 14 bytes "
                "per element, against 16 for 4 binary32 partials)")},
        "traces": {
            "real_moe_instances": ntok["real"], "real_positions": REAL_POSITIONS,
            "real_tokens": [int(t) for t in real["tokens"]],
            "real_layers": 40, "random_moe_instances": ntok["random"],
            "real_kv_rows": len(real["kv"]), "real_selections": len(real["sel"]),
            "kv_vectors": kvinfo, "argmax_tokens_real": len(real["logits"]), "argmax_tokens_random": N_RANDOM_LOGITS},
        "moe_cases": moe,
        "kv_argmax_cases": kv,
        "tensor_allreduce_cases": allreduce,
        "summary": {
            "moe_tokens_checked_bit_exact": sum(c["done"] for c in moe if c["pass"]),
            "dispatch_control_latency_cycles": sus["dsp_lat_min"],
            # input refused while the output was free, without back-pressure anywhere (under back-pressure the
            # two registered-ready slices take up to two cycles to reopen, which the stress cases count apart)
            "dispatch_control_bubbles_multicast_unstressed": sum(
                c["dsp_bubble"] for c in moe if c["build"].startswith("multicast") and not c["plusargs"].get("bp")),
            "dispatch_input_stalls_after_backpressure_multicast": sum(
                c["dsp_bubble"] for c in moe if c["build"].startswith("multicast") and c["plusargs"].get("bp")),
            "dispatch_flits_per_token_multicast": sus["dispatch_flits_per_token"],
            "dispatch_flits_per_token_unicast": sus_u["dispatch_flits_per_token"],
            "dispatch_records_per_token_unicast": sus_u["dispatch_records_per_token"],
            "combine_ingest_bound_cycles_per_token": ingest_bound,
            "sustained_cycles_per_token_real": sus["steady_cycles_per_token"],
            "sustained_cycles_per_token_random": rand_s["steady_cycles_per_token"],
            "sustained_return_messages_per_cycle": round(NR / sus["steady_cycles_per_token"], 4),
            "sustained_return_flits_per_cycle": round(ingest_bound / sus["steady_cycles_per_token"], 4),
            "sustained_cycles_per_token_by_tags": {
                str(t): case(b, "random_sustained")["steady_cycles_per_token"]
                for t, b in ((8, "multicast"), (4, "multicast_tags4"), (2, "multicast_tags2"))},
            "lone_token_latency_cycles_min": lone["lat_min"], "lone_token_latency_cycles_max": lone["lat_max"],
            "lone_token_latency_cycles_min_unicast": lone_u["lat_min"],
            "lone_token_remote_round_trip_cycles_min": lone["round_trip_min"],
            "lone_token_remote_ingest_span_cycles": lone["ingest_span_min"],
            "combine_control_latency_cycles_min": lone["cmb_lat_min"],
            "link_first_flit_latency_cycles": HOP,
            "lone_token_latency_law": {
                "two_hops_cycles": 2 * HOP,
                "remote_results_serialised_flits": (NR - 1) * (1 + VEC_FLITS),
                "engine_and_model_cycles": lone["lat_min"] - 2 * HOP - (NR - 1) * (1 + VEC_FLITS)},
            "kv_multicast_latency_by_hops_min": {str(h): hops[h]["min_cycles"] for h in per_hop},
            "kv_node_cycles_beyond_links_by_hops": {str(h): node_overhead[h] for h in per_hop},
            "tensor_allreduce_cycles_per_reduction": allreduce[0]["cycles_per_reduction"],
            "tensor_allreduce_ingest_bound_cycles": AR_DIES * (1 + AR_FLITS),
            "argmax_first_token_cycles": am["first"],
            "argmax_steady_cycles_per_token": round((am["q3"] - am["q1"]) / max(1, (3 * am["tokens"]) // 4 - am["tokens"] // 4), 3),
            "argmax_beats_per_slice": -(-SLICE // LANES_AM)},
        "verilator_lint": {"flags": list(LINT_FLAGS), **lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                         sorted(set(ENGINES + [LINK, ADD, *AQ, ROUTER, TB_MOE, TB_KV, TB_AR, HARNESS, *TOOLS]))},
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--scratch", type=Path, default=None, help="keep vectors and builds here")
    parser.add_argument("--jobs", type=int, default=5)
    args = parser.parse_args()
    if args.scratch:
        args.scratch.mkdir(parents=True, exist_ok=True)
        record = run_campaign(args.scratch, args.jobs)
    else:
        with tempfile.TemporaryDirectory() as d:
            record = run_campaign(Path(d), args.jobs)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    s = record["summary"]
    print(record["status"], {k: s[k] for k in ("moe_tokens_checked_bit_exact", "sustained_cycles_per_token_real",
                                                "lone_token_latency_cycles_min", "dispatch_control_latency_cycles",
                                                "combine_control_latency_cycles_min")})
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
