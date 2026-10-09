#!/usr/bin/env python3
"""Qwen3-8B on the r25 die through HGI-1: per-layer-type exact stage runs at the target position and a full token,
simulator (functional) vs the qwen_r25 golden, bit for bit.

    python3 -m hgi_sim.qwen_proof --snapshot SNAP --cache IMGDIR --stage layer --layer 0 --position 8191 --out R.json
    python3 -m hgi_sim.qwen_proof ... --stage head
    python3 -m hgi_sim.qwen_proof ... --stage token --position 8191          (embedding + 36 layers + head)

A stage run compiles the real program (tools/hgi_sim/qwen_compiler.py), encodes it to an HGI-1 image, loads the
Qwen model descriptor through the config path (CFG commit, every check), builds the four dies' HBM images (the
deployed INT8 image, the KV cache of a synthetic format-valid state at the position), drives the stage input into
the VM (the stage bench's input), rings the doorbell, and compares every family's result buffer on every die with the
golden's value of that family.  Negative mutants (rope_half = 0; KV heads swapped between the two planes; a QK-norm
published BF16) must fail.  Qwen's dense layers are all one type, so the layer stage is the per-layer-type run.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hbm_generic_iface as HGI  # noqa: E402
import qwen_r25_golden as R  # noqa: E402

from hgi_sim import lib as A  # noqa: E402
from hgi_sim import qwen_compiler as QC  # noqa: E402
from hgi_sim.machine import UNITS, Die, Fault, Machine  # noqa: E402
from hgi_sim.records import decode_program, encode_program  # noqa: E402

F = np.float32
MD_HEX = ROOT / "results/arch/hbm_generic_iface_20261009/md_qwen3_8b.hex"


def md_words(cfg):
    """The committed Qwen3-8B descriptor when the config is the released one; else one encoded the same way."""
    if cfg.get("hidden_size") == 4096 and cfg.get("vocab_size") == 151936 and MD_HEX.exists():
        return [int(x, 16) for x in MD_HEX.read_text().split()]
    import tempfile
    p = Path(tempfile.mkdtemp()) / "config.json"
    p.write_text(json.dumps(cfg))
    HGI.MODELS["_test"] = dict(cfg=str(p), model_class=2, tp=4, head_rows=cfg["vocab_size"] // 4)
    md, _ = HGI.from_config("_test")
    md["norm_d_units"] = 32           # test shapes only: the norm engine's legal widths are 4,096 / 5,120
    return HGI.pack(md)


def bits(a):
    return np.ascontiguousarray(np.asarray(a, dtype=F)).view(np.uint32)


class Checker:
    def __init__(self):
        self.rows = []

    def eq(self, family, what, die, got, want):
        g, w = bits(got).reshape(-1), bits(want).reshape(-1)
        ok = g.shape == w.shape and bool(np.array_equal(g, w))
        bad = None if ok else (int(np.nonzero(g != w)[0][0]) if g.shape == w.shape else "shape")
        self.rows.append(dict(family=family, what=what, die=die, n=int(w.size), bit_exact=ok, first_bad=bad))
        return ok


def vmget(die, g, name, n, off=0):
    return die.vm[g.vm[name] + off:g.vm[name] + off + n].view(F).copy()


def run_stage(model, cfg, stage, layer, pos, mutant=None, log=print):
    tok_in = 0
    ctx = 8192 if cfg["hidden_size"] == 4096 else max(64, pos + 1)
    g = QC.Geometry(cfg, ctx)
    words = md_words(cfg)
    md = HGI.unpack(words)
    tr = {}
    if stage == "layer":
        Kc, Vc = R.synthetic_kv(model, layer, pos)
        x = R.synthetic_x(model, layer)
        x_out = model.layer(layer, x, pos, Kc.copy(), Vc.copy(), tr)
        layers, kvs = [layer], {layer: (Kc, Vc)}
        parts = ("layers",)
    elif stage == "head":
        x = R.synthetic_x(model, 1)
        model.head(x, tr)
        layers, kvs, parts = [], {}, ("head",)
    elif stage == "token":
        tok_in = 9707 % model.V
        layers = list(range(model.L))
        kvs = {i: R.synthetic_kv(model, i, pos) for i in layers}
        x = model.embed(tok_in)
        tr["x_layers"] = []
        for i in layers:
            Kc, Vc = kvs[i]
            x = model.layer(i, x, pos, Kc.copy(), Vc.copy())
            tr["x_layers"].append(x)
            log(f"golden layer {i}")
        model.head(x, tr)
        x = None
        parts = ("embed", "layers", "head")
    else:
        raise ValueError(stage)
    hbms, _ = QC.build_images(model, g, layers, kv_state=kvs.get)
    if mutant == "kv_swap":
        # the die's two KV heads' planes exchanged (one KV head a die: its K and V planes exchanged)
        span = 2 * g.kv_plane if g.nk >= 2 else g.kv_plane
        for hb in hbms:
            buf, off, _ = hb.find(g.hbm["KV"], g.kv_layer)
            a = buf[off:off + span].copy()
            buf[off:off + span] = buf[off + span:off + 2 * span]
            buf[off + span:off + 2 * span] = a
    recs = QC.program(g, md, len(layers), parts=parts)
    if mutant == "qknorm_bf16":
        for r in recs:
            if r.tag.startswith("qknorm"):
                r.desc["O"].fmt = "BF16"
    image = encode_program(recs)
    assert encode_program(decode_program(image)) == image, "record encode / decode round trip"
    dies = [Die(d, hbms[d]) for d in range(QC.TP)]
    M = Machine(dies, UNITS)
    w2 = list(words)
    if mutant == "rope_adjacent":
        md2 = dict(md, rope_half=0)
        w2 = HGI.pack(md2)
    err = M.cfg_commit(w2)
    if err:
        raise SystemExit(f"CFG commit refused: {HGI.ERR[err]}")
    if x is not None:
        for d in dies:
            d.vm[g.vm["X"]:g.vm["X"] + g.H] = bits(x)
    snaps = {}

    def hook(Mm, r, L):
        if stage == "token":
            if r.tag == "row_scale_down+residual":
                snaps[("x", L)] = [d.vm[g.vm["X"]:g.vm["X"] + g.H].copy() for d in dies]
            elif r.tag in ("head_scale", "embedding.dequant"):
                snaps[r.tag] = [d.vm.copy() for d in dies]
            return
        snaps[r.tag] = [d.vm.copy() for d in dies]
    orig = Machine.run

    def run_with_hook(self, image, token, pos):
        from hgi_sim.records import decode_program as dp
        recs_ = dp(image)
        tags = [r.tag for r in recs]
        for r, t in zip(recs_, tags):
            r.tag = t
        return _run(self, recs_, token, pos, hook)
    t0 = time.time()
    try:
        tok, trace = run_with_hook(M, image, tok_in if stage == "token" else 0, pos)
    except Fault as e:
        return dict(stage=stage, layer=layer, position=pos, mutant=mutant, fault=str(e), status=e.status,
                    pass_=False, records=len(recs), image_bytes=len(image))
    wall = time.time() - t0
    C = Checker()
    H, HD, nq, nk = g.H, g.HD, g.nq, g.nk
    if stage == "token":
        for d in range(QC.TP):
            C.eq("embedding", "x0", d, snaps["embedding.dequant"][d][g.vm["X"]:g.vm["X"] + H].view(F),
                 model.embed(tok_in))
            for i in layers:
                C.eq("layer", f"x_out L{i}", d, snaps[("x", i)][d].view(F), tr["x_layers"][i])
            r0, r1 = model.head_rows(d)
            vm = snaps["head_scale"][d]
            C.eq("head+head_scale", "logits", d, vm[g.vm["LOG"]:g.vm["LOG"] + g.hrows].view(F), tr["logits"][r0:r1])
        C.rows.append(dict(family="argmax_local+argmax_merge+end", what="token", die=-1, n=1,
                           bit_exact=int(tok) == int(tr["token"][0]), first_bad=None if int(tok) == int(tr["token"][0])
                           else [int(tok), int(tr["token"][0])]))
    for d, die in enumerate(dies if stage != "token" else []):
        if stage == "head":
            r0, r1 = model.head_rows(d)
            vm = snaps["head_scale"][d]
            C.eq("head+head_scale", "logits", d, vm[g.vm["LOG"]:g.vm["LOG"] + g.hrows].view(F), tr["logits"][r0:r1])
            continue
        q, k, v = model.die_rows(d)
        rows = np.concatenate([q, k, v])
        s = lambda tag: snaps[tag][d]                          # noqa: E731

        def at(tag, name, n, off=0):
            return s(tag)[g.vm[name] + off:g.vm[name] + off + n].view(F)
        C.eq("prenorm", "attn", d, at("prenorm.attn", "H", H), A.to_bf16(tr["h_attn"]))
        C.eq("qkv+row_scale_qkv", "qkv", d, at("row_scale_qkv", "QKV", len(rows)), tr["qkv"][rows])
        hq = slice(d * nq, (d + 1) * nq)
        hk = slice(d * nk, (d + 1) * nk)
        C.eq("qknorm", "q", d, at("qknorm.k", "QN", nq * HD), tr["q_norm"][hq])
        C.eq("qknorm", "k", d, at("qknorm.k", "QN", nk * HD, nq * HD), tr["k_norm"][hk])
        C.eq("rope", "q", d, at("rope", "QR", nq * HD), tr["q_rope"][hq])
        C.eq("round_q", "q_bf16", d, at("round_q", "QB", nq * HD), A.to_bf16(tr["q_rope"][hq]))
        kvb, _, _ = die.hbm.find(g.hbm["KV"], g.kv_layer)
        from hgi_sim.machine import e4m3_table
        tab = e4m3_table()
        for h in range(nk):
            o = (h * 2) * g.kv_plane + pos * HD
            C.eq("kv_append", f"K{h}", d, tab[kvb[o:o + HD]], tr["k_row"][d * nk + h])
            o = (h * 2 + 1) * g.kv_plane + pos * HD
            C.eq("kv_append", f"V{h}", d, tab[kvb[o:o + HD]], tr["v_row"][d * nk + h])
        P = pos + 1
        sc = np.stack([at("attention_qk.kv%d" % (nk - 1), "SC", P, j * g.ctx) for j in range(nq)])
        C.eq("attention_qk", "scores*scale", d, A.mul(sc, F(np.uint32(md["attn_scale"]).view(F))), tr["scores"][hq])
        C.eq("softmax", "Z", d, at("softmax.exp_sum", "Z", nq), tr["Z"][hq])
        C.eq("attention_pv", "pv", d, at("attention_pv.kv%d" % (nk - 1), "PV", nq * HD), tr["pv"][hq])
        C.eq("pv_normalize", "attn", d, at("pv_normalize", "ATTN", nq * HD), tr["attn"][hq])
        C.eq("o", "partial", d, at("o", "OPART", H), tr["o_parts"][d])
        C.eq("all_reduce_o+row_scale_o+residual", "x_mid", d, at("row_scale_o+residual", "X", H), tr["x_mid"])
        C.eq("prenorm", "ffn", d, at("prenorm.ffn", "H", H), A.to_bf16(tr["h_ffn"]))
        gr = np.concatenate([np.arange(d * g.ff, (d + 1) * g.ff), g.FF + np.arange(d * g.ff, (d + 1) * g.ff)])
        C.eq("gu+row_scale_gu", "gu", d, at("row_scale_gu", "GU", 2 * g.ff), tr["gu"][gr])
        C.eq("swiglu", "act", d, at("swiglu", "ACT", g.ff), A.to_bf16(tr["act"][d * g.ff:(d + 1) * g.ff]))
        C.eq("down", "partial", d, at("down", "DPART", H), tr["down_parts"][d])
        C.eq("all_reduce_down+row_scale_down+residual", "x_out", d, at("row_scale_down+residual", "X", H),
             tr["x_out"])
    ok = all(r["bit_exact"] for r in C.rows)
    fams = {}
    for r in C.rows:
        f = fams.setdefault(r["family"], dict(checks=0, exact=0))
        f["checks"] += 1
        f["exact"] += int(r["bit_exact"])
    return dict(stage=stage, layer=layer, position=pos, mutant=mutant, pass_=ok, records=len(recs),
                image_bytes=len(image), executed_records=len(trace), wall_s=round(wall, 1), families=fams,
                failures=[r for r in C.rows if not r["bit_exact"]][:20],
                record_families=sorted({r.family for r in recs}), token=tok)


def _run(M, recs, token, pos, hook):
    """Machine.run over decoded records with a per-record hook (the stage bench's buffer capture)."""
    M.doorbell(token, pos)
    trace = []
    pc, loop, L = 0, None, 0
    while pc < len(recs):
        r = recs[pc]
        for die in M.dies:
            die.dyn[4] = L
        if r.unit == "CTL":
            if r.op == "LOOP":
                loop, L, pc = dict(start=pc + 1, count=r.param), 0, pc + 1
                continue
            if r.op == "ENDLOOP":
                L += 1
                if L < loop["count"]:
                    pc = loop["start"]
                    continue
                loop, L, pc = None, 0, pc + 1
                continue
            if r.op == "END":
                tok = int(M.dies[0].vm[r.desc["A"].base])
                return tok, trace
            pc += 1
            continue
        UNITS[(r.unit, r.op)](M, r, L)
        trace.append((pc, L, r.tag))
        hook(M, r, L)
        pc += 1
    raise Fault(2, "no END")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--stage", default="layer", choices=("layer", "head", "token"))
    ap.add_argument("--layer", type=int, default=0)
    ap.add_argument("--position", type=int, default=8191)
    ap.add_argument("--mutants", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    model = R.QwenR25(a.snapshot, a.cache)
    cfg = model.ck.cfg
    res = [run_stage(model, cfg, a.stage, a.layer, a.position)]
    print(json.dumps({k: v for k, v in res[0].items() if k != "failures"}, indent=1), flush=True)
    if a.mutants and a.stage == "layer":
        for mu in ("rope_adjacent", "kv_swap", "qknorm_bf16"):
            r = run_stage(model, cfg, a.stage, a.layer, a.position, mutant=mu)
            res.append(r)
            print(mu, "pass" if r["pass_"] else "FAILS (expected)", flush=True)
    ok = res[0]["pass_"] and all(not r["pass_"] for r in res[1:])
    rec = dict(schema="opentallas.hgi_sim.qwen_proof.v1", status="pass" if ok else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               host=os.uname().nodename, snapshot=a.snapshot.name, stage=a.stage, layer=a.layer, position=a.position,
               runs=res, spec="HGI-1 v0.9 (024fa2af1)",
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/records.py", "hgi_sim/lib.py", "hgi_sim/machine.py", "hgi_sim/qwen_compiler.py",
                   "hgi_sim/qwen_proof.py", "qwen_r25_golden.py", "hbm_generic_iface.py")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print(rec["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
