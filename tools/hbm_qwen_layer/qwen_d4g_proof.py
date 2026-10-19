#!/usr/bin/env python3
"""TOKEN-PASS-HBMQ (10-18): Qwen3-8B on the d4g GEN2 die (TP-8, 16 SM, 2 stacks) -- the compiled layer programmes
(hgi_sim.qwen_compiler Geometry(tp=8), the D4G8 mapping) run on the HGI-1 functional model against the qwen_r25
golden (TP-4 order of record), bit for bit, and the golden FIXTURES the RTL layer vehicle consumes.

Why D4G8 is the golden's arithmetic (no numerics change):
  o_proj   K = 4,096 split 8 x 512 = 64 chunks a die; the golden's TP-4 die partial is a csum8 over 128 chunks whose
           pairwise tree splits at 64, so ((q0 + q1) + (q2 + q3)) + ((q4 + q5) + (q6 + q7)) == ((P0 + P1) + (P2 + P3)).
  down     K = 12,288 split 4 x 3,072 = 384 chunks (padded tree of 512): NOT a 2-way split at 1,536, so a plain TP-8
           even split changes the rounding (witness below).  D4G8: rank q = 4 r + j computes the WHOLE TP-4 slice-j
           partial for output-row half r (2,048 rows, K 3,072; the same bytes / MACs a die as the even split) after an
           ALL_GATHER of the SwiGLU outputs; COLL.GROUP_REDUCE_MCAST s 4 reduces each row half over ranks 4r..4r+3 in
           rank (= j) order and multicasts [half 0 | half 1].
  qkv / gate-up / lm_head / attention: rows or heads split, order unchanged.

Stages (position 8191, synthetic format-valid KV state, synthetic_x inputs as qwen_proof):
  L0     one layer programme (parts=layers, 1 layer)          -- the cold layer
  chain  a 2-layer LOOP programme (L0 -> L1 chained)          -- the steady-state chained layer
  head   final norm + lm_head + argmax + merge
Checks every family on every die; DUT mutants (must FAIL): kv_swap, qknorm_bf16, rkj_wrong (down reads slice
3 - j), grm_s8 (down reduced as one 8-rank sub-group); head: head_swap (dies 0 / 1 lm_head shards exchanged).  Numerics witness: the plain TP-8 even down split differs
from the golden (counted, not a mutant of this programme).

    python3 tools/hbm_qwen_layer/qwen_d4g_proof.py --snapshot SNAP --cache IMG --stage L0 --mutants \
        --dump FIXDIR --out REC.json
"""
from __future__ import annotations

import argparse
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
from hgi_sim.machine import UNITS, Die, Fault, Machine, e4m3_table  # noqa: E402
from hgi_sim.records import decode_program, encode_program  # noqa: E402

F = np.float32
TP = 8


def md_words_d4g():
    """the Qwen3-8B HGI-1 descriptor with the d4g collective group (8); everything else as the committed TP-4 one"""
    _, _, md, _ = HGI.d_build("qwen3_8b")
    md = dict(md, coll_group_size=TP)
    w = HGI.d_pack(md)
    assert HGI.d_hw_check(w) == 0
    return w


def bits(a):
    return np.ascontiguousarray(np.asarray(a, dtype=F)).view(np.uint32)


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


class Checker:
    def __init__(self):
        self.rows = []
        self.expect = {}

    def eq(self, family, what, die, got, want):
        g, w = bits(got).reshape(-1), bits(want).reshape(-1)
        ok = g.shape == w.shape and bool(np.array_equal(g, w))
        bad = None if ok else (int(np.nonzero(g != w)[0][0]) if g.shape == w.shape else "shape")
        self.rows.append(dict(family=family, what=what, die=die, n=int(w.size), bit_exact=ok, first_bad=bad))
        self.expect[f"d{die}.{family}.{what}"] = w
        return ok


def golden(model, stage, pos):
    tr, kvs, x = {}, {}, None
    if stage == "L0":
        layers = [0]
    elif stage == "chain":
        layers = [0, 1]
    else:
        layers = []
    if layers:
        x = R.synthetic_x(model, layers[0])
        xi = x
        tr["layers"] = []
        for i in layers:
            Kc, Vc = R.synthetic_kv(model, i, pos)
            kvs[i] = (Kc, Vc)
            t = {}
            xi = model.layer(i, xi, pos, Kc.copy(), Vc.copy(), t)
            tr["layers"].append(t)
    else:
        x = R.synthetic_x(model, 1)
        model.head(x, tr)
    return layers, kvs, x, tr


def run_stage(model, cfg, stage, pos, mutant=None, dump=None, gold=None, log=print):
    ctx = 8192 if cfg["hidden_size"] == 4096 else max(64, pos + 1)
    g = QC.Geometry(cfg, ctx, tp=TP)
    words = md_words_d4g()
    md = QC.qwen_params(cfg)
    layers, kvs, x, tr = gold
    parts = ("layers",) if layers else ("head",)
    hbms, _ = QC.build_images(model, g, layers, kv_state=kvs.get)
    if mutant == "kv_swap":                      # one KV head a die: its K and V planes exchanged
        for hb in hbms:
            buf, off, _ = hb.find(g.hbm["KV"], g.kv_layer)
            a = buf[off:off + g.kv_plane].copy()
            buf[off:off + g.kv_plane] = buf[off + g.kv_plane:off + 2 * g.kv_plane]
            buf[off + g.kv_plane:off + 2 * g.kv_plane] = a
    if mutant == "rkj_wrong":                    # the per-die down slice table names slice 3 - j
        for d, hb in enumerate(hbms):
            buf, off, _ = hb.find(g.hbm["TABLES"] + g.tables["rkj"], 256)
            buf[off:off + 256] = np.full(64, 3 - d % 4, dtype=np.uint32).view(np.uint8)
    if mutant == "head_swap":                    # dies 0 and 1 hold each other's lm_head row shard
        a, b = (hb.find(g.hbm["HEAD"], 1) for hb in hbms[:2])
        t = a[0].copy()
        a[0][:] = b[0]
        b[0][:] = t
    recs = QC.program(g, md, len(layers), parts=parts)
    if mutant == "qknorm_bf16":
        for r in recs:
            if r.tag.startswith("qknorm"):
                r.desc["O"].fmt = "BF16"
    if mutant == "grm_s8":
        for r in recs:
            if r.tag == "all_reduce_down":
                r.param = 8
    image = encode_program(recs)
    assert encode_program(decode_program(image)) == image, "record encode / decode round trip"
    dies = [Die(d, hbms[d]) for d in range(TP)]
    M = Machine(dies, UNITS)
    err = M.cfg_commit(list(words))
    if err:
        raise SystemExit(f"CFG commit refused: {HGI.ERR[err]}")
    for d in dies:                               # the stage input (layer input / final hidden) into every die's VM
        d.vm[g.vm["X"]:g.vm["X"] + g.H] = bits(x)
    snaps = {}

    def hook(Mm, r, L):
        snaps[(r.tag, L)] = [d.vm.copy() for d in dies]
        if r.tag == "head_scale":
            snaps["logits"] = [d.stream_seen[1].copy() for d in dies]

    recs_ = decode_program(image)
    for r, r0 in zip(recs_, recs):
        r.tag, r.family = r0.tag, r0.family
    t0 = time.time()
    try:
        tok, trace = M.run(image, 0, pos, hash_bufs=False, hook=hook, recs=recs_)
    except Fault as e:
        return dict(stage=stage, position=pos, mutant=mutant, fault=str(e), status=e.status, pass_=False,
                    records=len(recs), image_bytes=len(image))
    wall = time.time() - t0
    C = Checker()
    H, HD, nq, nk = g.H, g.HD, g.nq, g.nk
    witness = {}
    if not layers:
        for d in range(TP):
            r0, r1 = g.head_rows(d)
            C.eq("head+head_scale", "logits", d, snaps["logits"][d], tr["logits"][r0:r1])
        ok_t = int(tok) == int(tr["token"][0])
        C.rows.append(dict(family="argmax_local+argmax_merge+end", what="token", die=-1, n=1, bit_exact=ok_t,
                           first_bad=None if ok_t else [int(tok), int(tr["token"][0])]))
    for L, i in enumerate(layers):
        t = tr["layers"][L]
        codes_o, _ = model.img.get(f"L{i}.o")
        attn = t["attn"].reshape(-1)
        sub_o = [A.sm_int8(codes_o[:, d * nq * HD:(d + 1) * nq * HD], attn[d * nq * HD:(d + 1) * nq * HD])
                 for d in range(TP)]
        # the mapping claims, on the golden library: 8-way o tree == the golden's o partial tree
        witness[f"L{i}.o_tree_8_equals_golden"] = bool(np.array_equal(bits(A.pairwise(sub_o)),
                                                                     bits(A.pairwise(list(t["o_parts"])))))
        for d, die in enumerate(dies):
            at = lambda tag, name, n, off=0: snaps[(tag, L)][d][g.vm[name] + off:g.vm[name] + off + n].view(F)  # noqa
            q, k, v = g.qkv_rows(d)
            rows = np.concatenate([q, k, v])
            C.eq("prenorm", "attn", d, at("prenorm.attn", "H", H), A.to_bf16(t["h_attn"]))
            C.eq("qkv+row_scale_qkv", "qkv", d, at("row_scale_qkv", "QKV", len(rows)), t["qkv"][rows])
            hq, hk = slice(d * nq, (d + 1) * nq), slice(d * nk, (d + 1) * nk)
            C.eq("qknorm", "q", d, at("qknorm.k", "QN", nq * HD), t["q_norm"][hq])
            C.eq("qknorm", "k", d, at("qknorm.k", "QN", nk * HD, nq * HD), t["k_norm"][hk])
            C.eq("rope", "q", d, at("rope", "QR", nq * HD), t["q_rope"][hq])
            C.eq("round_q", "q_bf16", d, at("round_q", "QB", nq * HD), A.to_bf16(t["q_rope"][hq]))
            kvb, kvo, _ = die.hbm.find(g.hbm["KV"] + L * g.kv_layer, g.kv_layer)
            tab = e4m3_table()
            for h in range(nk):
                o = kvo + (h * 2) * g.kv_plane + pos * HD
                C.eq("kv_append", f"K{h}", d, tab[kvb[o:o + HD]], t["k_row"][d * nk + h])
                o = kvo + (h * 2 + 1) * g.kv_plane + pos * HD
                C.eq("kv_append", f"V{h}", d, tab[kvb[o:o + HD]], t["v_row"][d * nk + h])
            P = pos + 1
            sc = np.stack([at("attention_qk.kv0", "SC", P, jj * g.ctx) for jj in range(nq)])
            C.eq("attention_qk", "scores*scale", d, A.mul(sc, F(np.uint32(md["attn_scale"]).view(F))),
                 t["scores"][hq])
            C.eq("softmax", "Z", d, at("softmax.exp_sum", "Z", nq), t["Z"][hq])
            C.eq("attention_pv", "pv", d, at("attention_pv.kv0", "PV", nq * HD), t["pv"][hq])
            C.eq("pv_normalize", "attn", d, at("pv_normalize", "ATTN", nq * HD), t["attn"][hq])
            C.eq("o", "partial8", d, at("o", "OPART", H), sub_o[d])
            C.eq("all_reduce_o+row_scale_o+residual", "x_mid", d, at("row_scale_o+residual", "X", H), t["x_mid"])
            C.eq("prenorm", "ffn", d, at("prenorm.ffn", "H", H), A.to_bf16(t["h_ffn"]))
            fc = g.ffn_cols(d)
            C.eq("gu+row_scale_gu", "gu", d, at("row_scale_gu", "GU", 2 * g.ff), t["gu"][np.concatenate([fc, g.FF + fc])])
            C.eq("swiglu", "act", d, at("swiglu", "ACTALL", g.ff, d * g.ff), A.to_bf16(t["act"][fc]))
            perm = np.concatenate([g.ffn_cols(qq) for qq in range(TP)])
            C.eq("act_all_gather", "act_all", d, at("act_all_gather", "ACTALL", g.FF), A.to_bf16(t["act"][perm]))
            dr, _ = g.down_block(d)
            C.eq("down", "partial_tp4_rowhalf", d, at("down", "DPART", g.drows), t["down_parts"][d % 4][dr])
            C.eq("all_reduce_down+row_scale_down+residual", "x_out", d, at("row_scale_down+residual", "X", H),
                 t["x_out"])
        # numerics witness: the plain TP-8 even split of down (each die 1,536 contiguous K, 8-rank pairwise tree)
        codes_d, sc_d = model.img.get(f"L{i}.down")
        mb = t["act"]
        ke = g.FF // TP
        ev = [A.sm_int8(codes_d[:, d * ke:(d + 1) * ke], mb[d * ke:(d + 1) * ke]) for d in range(TP)]
        dn_even = A.mul(A.pairwise(ev), sc_d)
        x2_even = A.add(t["x_mid"], dn_even)
        witness[f"L{i}.plain_tp8_even_down_differs"] = dict(
            down_elems_differ=int(np.sum(bits(dn_even) != bits(t["down"]))),
            x_out_elems_differ=int(np.sum(bits(x2_even) != bits(t["x_out"]))), of=int(H))
    ok = all(r["bit_exact"] for r in C.rows) and all(v is True for k, v in witness.items() if k.endswith("golden"))
    fams = {}
    for r in C.rows:
        f = fams.setdefault(r["family"], dict(checks=0, exact=0))
        f["checks"] += 1
        f["exact"] += int(r["bit_exact"])
    res = dict(stage=stage, position=pos, mutant=mutant, pass_=ok, records=len(recs), image_bytes=len(image),
               image_sha256=hashlib.sha256(image).hexdigest(), executed_records=len(trace), wall_s=round(wall, 1),
               families=fams, failures=[r for r in C.rows if not r["bit_exact"]][:20], numerics_witness=witness,
               token=int(tok))
    if dump and mutant is None:
        res["fixture"] = write_fixture(Path(dump) / stage, g, words, image, hbms, x, layers, C, pos)
    return res


def write_fixture(out, g, words, image, hbms, x, layers, C, pos):
    """the RTL vehicle's inputs and expected values (binary, on the fleet scratch) + a sha256 manifest (committed)"""
    out.mkdir(parents=True, exist_ok=True)
    man = dict(position=pos, layers=layers, tp=TP, files={})

    def put(name, arr):
        a = np.ascontiguousarray(arr)
        (out / name).write_bytes(a.tobytes())
        man["files"][name] = dict(bytes=int(a.nbytes), dtype=str(a.dtype), sha256=sha(a))
    put("program.hgi1", np.frombuffer(image, dtype=np.uint8))
    put("md_qwen3_8b_d4g.u32", np.asarray(words, dtype=np.uint32))
    if x is not None:
        put("x_in.f32", np.asarray(x, dtype=F))
    for d, hb in enumerate(hbms):
        for base, data, name in hb.regions:
            if name == "EMBED" and layers:
                continue                       # the layer stages never read the embedding table
            put(f"die{d}.hbm_{name}_{base:#x}.u8", data)
    exp = {k: v for k, v in C.expect.items()}
    np.savez(out / "expected.npz", **exp)
    man["expected"] = {k: dict(n=int(v.size), sha256=sha(v)) for k, v in exp.items()}
    man["vm_map_words"] = g.vm
    (out / "manifest.json").write_text(json.dumps(man, indent=1, default=int) + "\n")
    return dict(dir=str(out), files=len(man["files"]), expected=len(exp),
                manifest_sha256=hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--stage", default="L0", choices=("L0", "chain", "head"))
    ap.add_argument("--position", type=int, default=8191)
    ap.add_argument("--mutants", action="store_true")
    ap.add_argument("--dump", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    model = R.QwenR25(a.snapshot, a.cache)
    cfg = model.ck.cfg
    gold = golden(model, a.stage, a.position)
    tg = time.time() - t0
    res = [run_stage(model, cfg, a.stage, a.position, dump=a.dump, gold=gold)]
    print(json.dumps({k: v for k, v in res[0].items() if k != "failures"}, indent=1, default=int), flush=True)
    if a.mutants:
        mus = ("kv_swap", "qknorm_bf16", "rkj_wrong", "grm_s8") if a.stage != "head" else ("head_swap",)
        for mu in mus:
            r = run_stage(model, cfg, a.stage, a.position, mutant=mu, gold=gold)
            res.append(r)
            print(mu, "pass (BAD)" if r["pass_"] else "FAILS (expected)", r.get("fault", ""), flush=True)
    ok = res[0]["pass_"] and all(not r["pass_"] for r in res[1:])
    rec = dict(schema="opentallas.hbm_qwen_d4g_proof.v1", status="pass" if ok else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               host=os.uname().nodename, snapshot=a.snapshot.name, stage=a.stage, position=a.position,
               golden_s=round(tg, 1), wall_s=round(time.time() - t0, 1), runs=res,
               golden="qwen_r25 (TP-4 order of record, contract r25_prenorm_full_w8), permuted RoPE order (spec 7.2)",
               mapping="D4G8 (tools/hgi_sim/qwen_compiler.py Geometry tp=8)",
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/records.py", "hgi_sim/lib.py", "hgi_sim/machine.py", "hgi_sim/qwen_compiler.py",
                   "hbm_qwen_layer/qwen_d4g_proof.py", "qwen_r25_golden.py", "hbm_generic_iface.py")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print(rec["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
