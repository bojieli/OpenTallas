#!/usr/bin/env python3
"""DS-V4.1 HBM accelerator, 1M token (position 1,048,575): the dedicated-unit (DU) LOCAL steps of one TP-96 die that
tools/dshbm_baseline_measure.py still prices from the W19 model (index_q, index_scores, topk_local, cand_local,
cand_mask, engram_fetch / engram_mix, the FP8 quantisers, the router top-6), measured in full-shape RTL on die 0's
real operands (minimum-component rule: one unit per step), bit-exact against the golden-checked values.

Die 0's share of a scanning layer: the TP-96 executor shards index keys by sequence position in groups of KEY_BLOCK = 8,
group i on die (i // 8) mod 96 (tools/w19_hbm_tp96_isa.py `owned`): 5,462 keys at the ratio-2 layers (n = 524,288),
10,923 at the ratio-1 layers (n = 1,048,576).  The executor checks every die's scores against the W17 golden shard
(L*.index_scores, post candidate mask), so die 0's select / candidate inputs are the golden scores at its own keys.

    python3 tools/dshbm_1m_local.py select --gold DIR --work DIR          # topk_local (L2/L14/L20/L24) + cand_local (L20)
    python3 tools/dshbm_1m_local.py idx    --snaps local_snaps_ext.pkl --work DIR   # index scoring array, real keys
    python3 tools/dshbm_1m_local.py su-prep --snaps ... --out DIR         # index_q RoPE / weights scale, engram_mix chains
    python3 tools/dshbm_1m_local.py record --work DIR [--record results/rtl/dshbm_1m_allmeasured_20261004/local.json]

Everything heavy runs on the compute hosts (owner rule 2026-10-04: nothing heavy on localhost).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

F = np.float32
TP, KEY_BLOCK, RANK = 96, 8, 0
FAST, SLOW = 1.2e9, 0.9e9
SCAN = {2: 524288, 8: 524288, 14: 524288, 20: 1048576, 24: 1048576}   # n keys of the layer's index scan
REC = ROOT / "results/rtl/dshbm_1m_allmeasured_20261004/local.json"
GOLD_DEFAULT = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def owned(n, r=RANK):
    """tools/w19_hbm_tp96_isa.Executor.owned: the keys < n die r owns (blocks of KEY_BLOCK, round robin)."""
    blocks = np.arange(r, -(-n // KEY_BLOCK), TP)
    idx = (blocks[:, None] * KEY_BLOCK + np.arange(KEY_BLOCK)[None, :]).reshape(-1)
    return idx[idx < n]


# ======================================================================================================================
# select: the die's local top-512 (ot_hdc_v41x_sel) and layer 20's candidate blocks (ot_hdc_v41x_sel_cand)
# ======================================================================================================================
def cmd_select(a):
    import hdc_golden_v41 as G
    import rtl_hdc_v41x_sel_campaign as S
    import rtl_hdc_v41x_sel_cand_campaign as C
    G.set_arith("chunk8")
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    Q, W, IW, K, AW = 4, 16, 20, 512, 8                     # the ROM's measured local select configuration
    jobs, meta = {}, {}
    rng = np.random.default_rng(0)
    for L in (2, 14, 20, 24):
        s = np.load(Path(a.gold) / f"ctx1048576_L{L:02d}.npz")[f"L{L}.index_scores"]
        n = SCAN[L]
        assert len(s) == n
        idx = owned(n)
        v = s[idx]
        bits = S.bf16_bits(v)
        assert np.array_equal(S.vals_of(bits), v, equal_nan=True)
        # golden f_topk_local: lexsort((idx, -v))[:k], k = min(512, len(idx))
        k = min(512, len(idx))
        gold_sel = idx[np.lexsort((idx, -v))[:k]]
        cuts = [(len(idx) * q) // Q for q in range(Q + 1)]     # the die's four HBM stacks hold its key quarters
        beats, exps = [], []
        sel = sorted(int(i) for i in G.topk_lowest_index(S.vals_of(bits), k))
        for q in range(Q):
            lo, hi = cuts[q], cuts[q + 1]
            beats.append(S.to_beats(rng, bits[lo:hi], idx[lo:hi], W, True))
            exps.append([(int(idx[i]), int(bits[i]), int(bits[i] == S.NINF)) for i in sel if lo <= i < hi])
        seg = (beats, k, exps, {"n": len(idx)})
        unit_sel = sorted(int(idx[i]) for i in sel)
        meta[f"L{L}"] = dict(layer=L, n_scan=n, keys_die0=int(len(idx)), finite=int(np.isfinite(v).sum()), k=k,
                             unit_reference_equals_executor_golden=bool(unit_sel == sorted(int(x) for x in gold_sel)))
        jobs[f"L{L}_topk"] = ("sel", seg, f"L{L}_topk_die0")
    # layer 20 candidates: block maxima over the die's 1,366 owned blocks (stored contiguously on the die)
    s = np.load(Path(a.gold) / "ctx1048576_L20.npz")["L20.index_scores"]
    n = SCAN[20]
    idx = owned(n)
    v = s[idx]
    bits = S.bf16_bits(v)
    nb_die = len(idx) // KEY_BLOCK
    blocks = np.arange(RANK, -(-n // KEY_BLOCK), TP)
    # golden f_cand_local: k = min(2048, nb, len(blocks)) of the die's blocks by (max desc, block asc); global newest
    # block pinned only if owned
    bs = v.reshape(-1, KEY_BLOCK).max(axis=1)
    k_c = min(2048, -(-n // KEY_BLOCK), len(blocks))
    gold_kept = sorted(int(b) for b in blocks[np.lexsort((blocks, -bs))[:k_c]])
    segc = C.segment(rng, bits, 2048, 16, Q=4, cut="even", cand_b=KEY_BLOCK, K=2048)
    unit_kept_global = sorted(int(blocks[b]) for q in range(4) for b in segc[2][q])
    meta["L20_cand"] = dict(layer=20, keys_die0=int(len(idx)), blocks_die0=int(nb_die), k=k_c,
                            unit_reference_equals_executor_golden=bool(unit_kept_global == gold_kept),
                            note="die-local contiguous storage: local block j = global block 96 j; the unit pins the "
                                 "die's last local block (+inf) -- harmless here: k (2,048) exceeds the die's 1,366 "
                                 "blocks, so every block is kept either way; the merge carries the TRUE block maxima")
    jobs["L20_cand"] = ("cand", segc, "L20_cand_die0")
    t0 = time.time()
    res = {}
    with cf.ThreadPoolExecutor(len(jobs)) as ex:
        fut = {}
        for name, (kind, seg, lab) in jobs.items():
            if kind == "sel":
                fut[name] = ex.submit(S.run_config, name, Q, W, IW, K, AW, [seg], [lab], work, ((0, 0, 1),))
            else:
                fut[name] = ex.submit(C.run_config, name, 4, 16, 20, 2048, 10, [seg], [lab], work, ((0, 0, 1),))
        for name, f in fut.items():
            res[name] = f.result()
    out = {}
    for name, cfg in res.items():
        r = cfg["runs"][0]
        ps = (r.get("per_segment") or [None])[0]
        cyc = None if ps is None else ps["last"] - ps["first"] + 1 + ps["tail"]
        mk = name.replace("_topk", "") if name.endswith("_topk") else "L20_cand"
        out[name] = dict(unit="ot_hdc_v41x_sel" if name.endswith("_topk") else "ot_hdc_v41x_sel_cand",
                         params=dict(Q=Q, W=W, IW=IW, K=K, AW=AW) if name.endswith("_topk") else
                         dict(Q=4, SL=16, IWP=20, K=2048, AW=10),
                         rtl_pass=cfg["pass"], errors=r.get("errors"), cycles=cyc,
                         ingest_cycles=None if ps is None else ps["last"] - ps["first"] + 1,
                         tail=None if ps is None else ps["tail"], ovf=None if ps is None else ps["ovf"],
                         replays=None if ps is None else ps["replays"], clock_hz=FAST,
                         us=None if cyc is None else round(cyc / FAST * 1e6, 4), vectors_sha256=cfg.get("vectors_sha256"),
                         log=None if cfg["pass"] else r.get("log"), **meta[mk])
        out[name]["exact"] = bool(cfg["pass"] and meta[mk]["unit_reference_equals_executor_golden"])
        print(name, out[name]["exact"], cyc, flush=True)
    srcs = {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(S.RTL + C.RTL + [S.TB, S.HARNESS, C.TB, C.HARNESS]))}
    srcs["tools/dshbm_1m_local.py"] = sha(ROOT / "tools/dshbm_1m_local.py")
    rec = dict(schema="opentallas.dshbm-1m.local.select.v1", generated_utc=now(), wall_s=round(time.time() - t0, 1),
               simulator=subprocess.run([S.VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
               golden_shards={f"L{L}": sha(Path(a.gold) / f"ctx1048576_L{L:02d}.npz") for L in (2, 14, 20, 24)},
               results=out, source_sha256=srcs,
               status="pass" if all(x["exact"] for x in out.values()) else "fail")
    (work / "select.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("SELECT", rec["status"])
    return 0 if rec["status"] == "pass" else 1


# ======================================================================================================================
# snapshots of the golden-checked TP-96 executor (tools/dshbm_baseline_measure.py execute --exec-layers L)
# ======================================================================================================================
def load_snaps(paths):
    snaps = {}
    for p in paths.split(","):
        snaps.update(pickle.loads(Path(p).read_bytes()))
    return snaps


def by_fn(snaps, fn, layer=None):
    return [(k, s) for k, s in sorted(snaps.items()) if s["op"]["fn"] == fn and (layer is None or s["op"]["layer"] == layer)]


# ======================================================================================================================
# idx: the indexer scoring array (W11 ot_hdc_v41x_idx_array, 64 keys a beat) on die 0's real keys / query / weights
# ======================================================================================================================
def cmd_idx(a):
    import hdc_golden as G
    import rtl_hdc_v41x_idx_campaign as C
    import rtl_w11_idx_array as A
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    snaps = load_snaps(a.snaps)
    exe, _ = A.build(work, 2, 4, jobs=16)
    W = 2 * 4
    out = {}
    tasks = []
    for key, s in by_fn(snaps, "index_scores"):
        L = s["op"]["layer"]
        b, af = s["before"], s["after"]
        q = np.asarray(b["iqf"], F).reshape(A.IH, A.NB * 32)
        w = np.asarray(b["iw"], F).reshape(-1)
        keys = np.asarray(s["keys"], F)
        idx = np.asarray(s["key_idx"], np.int64)
        assert np.array_equal(idx, np.asarray(af["is_i"], np.int64))
        post = np.asarray(af["is_v"], np.float64)
        cm = by_fn(snaps, "cand_mask", L)
        if cm:
            keepb = cm[0][1]["cand_keep"]
            keep = np.array([keepb[int(i) // KEY_BLOCK] for i in idx], dtype=bool)
            post = np.asarray(cm[0][1]["after"]["is_v"], np.float64)
        else:
            keep = np.ones(len(idx), dtype=bool)
        qc, qu = C.to_codes(q)
        kc, ku = C.to_codes(keys)
        tok = C.finish(dict(qc=qc, qu=qu, w=w, kc=kc, ku=ku, keep=keep, cls=f"L{L}.die0"))
        want = (G.bits(post.astype(F)) >> 16).astype(np.int64)
        ref_ok = bool(np.array_equal(np.asarray(tok["exp"], np.int64), want)) and not bool(np.any(tok["fault"]))
        m64 = A.contig_beats(len(idx), A.BEAT)
        parts = []
        for pp in range(A.BEAT // W):
            d = work / f"L{L}_p{pp}"
            ntok, nslot = A.write_mems(d, [(tok, m64[:, pp * W:(pp + 1) * W])], 4)
            tasks.append((L, pp, d, ntok, nslot))
        out[f"L{L}"] = dict(layer=L, keys_die0=int(len(idx)), beats=int(m64.shape[0]), masked=int((~keep).sum()),
                            reference_equals_executor=ref_ok, query_heads=A.IH)
        print(f"L{L}: keys {len(idx)} beats {m64.shape[0]} masked {int((~keep).sum())} ref==executor {ref_ok}",
              flush=True)
    with cf.ThreadPoolExecutor(min(32, len(tasks))) as ex:
        res = list(ex.map(lambda t: A.run(exe, t[2], t[3], t[4], seed=1), tasks))
    for (L, pp, d, ntok, nslot), r in zip(tasks, res):
        out[f"L{L}"].setdefault("parts", []).append(dict(part=pp, beat_slots=[pp * W, pp * W + W - 1], **r))
    for k, v in out.items():
        ps = v["parts"]
        v["errors"] = int(sum(x["errors"] for x in ps))
        v["checked"] = int(sum(x["checked"] for x in ps))
        v["cycles"] = int(max(x["tok_cycles"] for x in ps))
        v["span"] = int(max(x["span"] for x in ps))
        v["lat_max"] = int(max(x["lat_max"] for x in ps))
        v["in_stall"] = int(max(x["in_stall"] for x in ps))
        v["exact"] = bool(v["reference_equals_executor"] and v["errors"] == 0 and v["checked"] == v["keys_die0"])
        v["law"] = "query settle 24 + one 64-key beat a cycle + pipeline latency 48 (W11 element timing, II 1)"
        v["law_cycles"] = 24 + v["beats"] + 48
        v["us_1p2GHz"] = round(v["cycles"] / FAST * 1e6, 4)
        print(k, v["exact"], v["cycles"], v["law_cycles"], flush=True)
    rec = dict(schema="opentallas.dshbm-1m.local.idx.v1", generated_utc=now(), unit="ot_hdc_v41x_idx_array (W11, spec "
               "NS 16 x NK 4 = 64 keys a beat), composed from NS 2 / NK 4 runs over the beat's 8-slot windows (the W11 "
               "full-N method: the slices share only the beat handshake and the query load)", clock_hz=FAST,
               results=out, verilator=A.verilator_version(),
               source_sha256={p_: sha(ROOT / p_) for p_ in A.RTL + [A.TB, A.VLT, A.HARNESS,
                                                                    "tools/rtl_w11_idx_array.py",
                                                                    "tools/rtl_hdc_v41x_idx_campaign.py",
                                                                    "tools/dshbm_1m_local.py"]},
               status="pass" if out and all(v["exact"] for v in out.values()) else "fail")
    (work / "idx.json").write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print("IDX", rec["status"])
    return 0 if rec["status"] == "pass" else 1


# ======================================================================================================================
# quant: ot_hdc_actquant (FP8 / FP4 E8M0) on die 0's quantiser inputs (one instance, golden blocks)
# ======================================================================================================================
def cmd_quant(a):
    import hdc_golden_v41 as V
    import rtl_hdc_v41_blockdot_campaign as BC
    import rtl_v41_fullshape_layer_campaign as LC
    import re
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    snaps = load_snaps(a.snaps)
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    sets = {}
    for key, s in sorted(snaps.items()):
        op, b, af = s["op"], s["before"], s["after"]
        L = op["layer"]
        if op["fn"] == "hc_pre_norm":
            sets[f"L{L}.{op['which']}.quant"] = ("fp8", np.asarray(af["x"], F), None)
        elif op["fn"] == "q_norm_kv_row":
            sets[f"L{L}.q_quant"] = ("fp8", np.asarray(af["qr"], F), None)
            cs = V.rope_cs(m.freqs_yarn if m.ratio[L] > 0 else m.freqs_plain, 1048575)
            kv = V.rope_tail(V.rmsnorm_bf16(np.asarray(b["kvraw"], F), m.lw(L, "attn.kv_norm.weight"), m.eps), cs)
            sets[f"L{L}.kv_row_qdq"] = ("fp8", np.asarray(kv, F).reshape(-1), np.asarray(af["win_new"], F))
        elif op["fn"] == "index_q":
            q = V.rope_tail(np.asarray(b["iq"], F).reshape(s["ih"], s["ihd"]), s["cs"])
            sets[f"L{L}.idx_q_qdq"] = ("fp4", np.asarray(q, F).reshape(-1), np.asarray(af["iqf"], F))
    vl = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
    obj = work / "obj"
    exe = obj / "Vtb_dsrom_1m_quant"
    tb = ROOT / "rtl/test/dsrom_sys/tb_dsrom_1m_quant.sv"
    rtl = [ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv", ROOT / "rtl/hdc/v41/ot_hdc_fp4qdq.sv"]
    if not exe.exists():
        subprocess.run([str(vl), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module",
                        "tb_dsrom_1m_quant", "-Mdir", str(obj), *map(str, rtl), *map(str, BC.LIB), str(tb)],
                       check=True, capture_output=True)
    rows = []
    for node, (kind, x, want_exec) in sets.items():
        fp4 = kind == "fp4"
        blocks = x.reshape(-1, 32)
        d = work / node
        d.mkdir(exist_ok=True)
        ys = []
        with open(d / "aq_in.mem", "w") as fi, open(d / "aq_exp.mem", "w") as fe:
            for bl in blocks:
                fi.write(f"{int(fp4):01x}{BC.hexw(V.bits(bl), 32):0256x}\n")
                f_, e, codes, y = BC.aq_expect(bl, fp4)
                ys.append(np.asarray(y, np.uint32))
                fe.write(f"{f_:01x}{e & 0xFFF:03x}{BC.hexw(codes, 8):064x}{BC.hexw(y, 16):0128x}\n")
        yv = (np.concatenate(ys) << 16).view(F)
        gold = V.qdq_fp4_e8m0(x) if fp4 else V.qdq_fp8(x)
        golden_ok = bool(np.array_equal(V.bits(gold), V.bits(yv)))
        exec_ok = None if want_exec is None else bool(np.array_equal(V.bits(want_exec.reshape(-1)), V.bits(yv)))
        r = subprocess.run([str(exe), f"+NAQ={len(blocks)}"], cwd=d, capture_output=True, text=True).stdout
        mm = re.search(r"DSQ naq=(\d+) checked=(\d+) errors=(\d+) nq4=(\d+) checked=(\d+) errors=(\d+) "
                       r"first_in=(-?\d+) last_out=(-?\d+)", r)
        naq, ca, ea, _, _, _, fi_, lo_ = map(int, mm.groups())
        cyc = lo_ - fi_ + 1
        rows.append(dict(node=node, kind=kind, elements=int(len(x)), blocks=int(len(blocks)), unit="ot_hdc_actquant",
                         cycles_one_instance=cyc, latency_after_stream=cyc - len(blocks), clock_hz=SLOW,
                         us_one_instance=round(cyc / SLOW * 1e6, 4), errors=ea, checked=ca,
                         golden_function_check=golden_ok, executor_value_check=exec_ok,
                         exact=bool("PASS" in r and ea == 0 and ca == len(blocks) and golden_ok and exec_ok is not False)))
        print(node, kind, len(blocks), cyc, rows[-1]["exact"], flush=True)
    rec = dict(schema="opentallas.dshbm-1m.local.quant.v1", generated_utc=now(), rows=rows,
               note="one ot_hdc_actquant instance (32 elements a cycle), blocks back to back; the bench clock is the "
                    "unit's own cycle, priced in the serial 0.9 GHz domain as the ROM's quant.json does",
               source_sha256={str(p_.relative_to(ROOT)): sha(p_) for p_ in (*rtl, tb)},
               status="pass" if rows and all(r_["exact"] for r_ in rows) else "fail")
    (work / "quant.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("QUANT", rec["status"])
    return 0 if rec["status"] == "pass" else 1


# ======================================================================================================================
# su-prep: index_q (RoPE of the 32 heads' tails + weights scale) and engram_mix lowered to the HBM die's stream unit
# ======================================================================================================================
def cmd_su_prep(a):
    import hdc_golden as G
    import hdc_golden_v41 as V
    import hdc_isa_v41 as I
    import rtl_hdc_v41x_vec_campaign as VC
    import dshbm_baseline_measure as B
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    snaps = load_snaps(a.snaps)
    chains = []
    for key, s in sorted(snaps.items()):
        op, b, af = s["op"], s["before"], s["after"]
        L = op["layer"]
        if op["fn"] == "index_q":
            c = B.Chain(f"L{L}.index_q", VC)
            c.meta = dict(layer=f"L{L}", fn="index_q", op_id=op["id"], tag=op["tag"], reps=1, op_major=False)
            ih, ihd = s["ih"], s["ihd"]
            q = np.asarray(b["iq"], F).reshape(ih, ihd)
            cos, sin = s["cs"]
            rd = 2 * len(cos)
            Q = c.vm(q)
            tb = c.crom(cos, sin)
            O = c.buf(ih * ihd)
            c.op(nout=ih, nin=rd, abase=Q + ihd - rd, aso=ihd, asi=1, cpair=1, bsrc=I.SRC_CLO, bbase=tb, bso=0, bsi=1,
                 bhalf=1, dsrc=I.SRC_CHI, dbase=tb, dso=0, dsi=1, m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q, rnd=1,
                 obase=O + ihd - rd, oso=ihd, osi=1)
            want = V.rope_tail(q, s["cs"])
            assert np.array_equal(G.bits(V.qdq_fp4_e8m0(np.asarray(want, F).reshape(-1))),
                                  G.bits(np.asarray(af["iqf"], F).reshape(-1))), "qdq(rope(iq)) != executor iqf"
            for h in range(ih):           # the rotated tails, head by head (heads' first halves pass to the QDQ as is)
                c.check(f"index q RoPE tail h{h} (pre FP4 QDQ; qdq of it == executor iqf)", O + h * ihd + ihd - rd,
                        np.asarray(want, F)[h, ihd - rd:], "golden_fn")
            iwr = np.asarray(b["iwr"], F).reshape(-1)
            IWR = c.vm(iwr)
            IWo = c.buf(len(iwr))
            c.op(nout=1, nin=len(iwr), abase=IWR, aso=len(iwr), asi=1, m1=I.M1_AIMM, imm1=B.f32u(s["index_w_scale"]),
                 rnd=1, obase=IWo, oso=len(iwr), osi=1)
            c.check("iw (weights scale, BF16)", IWo, af["iw"])
            chains.append(c)
        elif op["fn"] == "engram_mix":
            c = B.Chain(f"L{L}.engram_mix", VC)
            c.meta = dict(layer=f"L{L}", fn="engram_mix", op_id=op["id"], tag=op["tag"], reps=1, op_major=False)
            hc, D = s["hc"], s["dim"]
            h = np.asarray(b["h"], F).reshape(hc, D)
            kv = np.asarray(b["eg_kv"], F).reshape(-1)
            key_, val = kv[:hc * D].reshape(hc, D), kv[hc * D:]
            H, K, VAL = c.vm(h), c.vm(key_), c.vm(val)
            Wc = c.crom(np.asarray(s["wgt"], F).reshape(-1))
            seg = 8
            SSH, SSK, DOT = [c.buf(8) for _ in range(hc)], [c.buf(8) for _ in range(hc)], [c.buf(8) for _ in range(hc)]
            RH, RK, RS, GT = ([c.buf(8) for _ in range(hc)] for _ in range(4))
            O = c.buf(hc * D)
            for j in range(hc):           # level-4 interleave: the four rows' independent reductions first
                c.op(nout=seg, nin=D // seg, abase=H + j * D, aso=D // seg, asi=1, red=I.RED_SUM, redsq=1, redtree=1,
                     rbase=SSH[j], dst=0)
                c.op(nout=seg, nin=D // seg, abase=K + j * D, aso=D // seg, asi=1, red=I.RED_SUM, redsq=1, redtree=1,
                     rbase=SSK[j], dst=0)
                c.op(nout=seg, nin=D // seg, abase=H + j * D, aso=D // seg, asi=1, bsrc=I.SRC_CLO, bbase=Wc + j * D,
                     bso=D // seg, bsi=1, m1=I.M1_AB, cbase=K + j * D, cso=D // seg, csi=1, m2=I.M2_C, red=I.RED_SUM,
                     redtree=1, rbase=DOT[j], dst=0)
            for j in range(hc):
                for ss, rr in ((SSH[j], RH[j]), (SSK[j], RK[j])):
                    c.op(nout=1, nin=1, abase=ss, m1=I.M1_DIVIMM, imm1=B.f32u(D), ad=I.AD_IMM, imm2=B.f32u(s["eps"]),
                         sfu=I.SFU_RSQRT, obase=rr)
            for j in range(hc):
                c.op(nout=1, nin=1, abase=RH[j], bbase=RK[j], m1=I.M1_AB, obase=RS[j])
            for j in range(hc):
                c.op(nout=1, nin=1, abase=DOT[j], bbase=RS[j], m1=I.M1_AB, m2=I.M2_IMM, imm1=B.f32u(s["engram_scale"]),
                     sfu=I.SFU_EGATE, obase=GT[j])
            for j in range(hc):
                c.op(nout=1, nin=D, abase=VAL, aso=D, asi=1, bbase=GT[j], m1=I.M1_AB, cbase=H + j * D, cso=D, csi=1,
                     ad=I.AD_C, rnd=1, obase=O + j * D, oso=D, osi=1)
            c.check("engram h (4 x 5120)", O, np.asarray(af["engram_h"], F).reshape(-1))
            chains.append(c)
    cases = [dict(name=c.name, meta=c.meta, init=c.init, cr_lo=c.cr_lo, cr_hi=c.cr_hi, ops=c.ops,
                  checks=[(lab, ad, G.bits(np.asarray(w, F)).astype(np.uint32), kind) for lab, ad, w, kind in c.checks])
             for c in chains]
    (out / "su_cases_local.pkl").write_bytes(pickle.dumps(dict(
        cases=cases, snapshots_sha256=hashlib.sha256("".join(sha(p_) for p_ in a.snaps.split(",")).encode()).hexdigest())))
    print("SU cases", [c["name"] for c in cases])
    return 0


# ======================================================================================================================
# engram: the checkpoint's Engram table rows the token reads (the 100 GB table shards are not copied to the compute
# host: a sparse stand-in holds the header, every non-table tensor of the layer and exactly the rows the hashes select)
# ======================================================================================================================
def cmd_engram_ids(a):
    """On the compute host (tokenizer + headers only): the hash ids of the reference token's Engram layers and the
    byte ranges of the shard that hold them and every other tensor of the layer's Engram block."""
    import rtl_v41_fullshape_layer_campaign as LC
    ref = json.loads((ROOT / "results/rtl/w17_v41_1m_reference_token.json").read_text())
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=True)
    out = {}
    for L in [int(x) for x in a.layers.split(",")]:
        li = m.engram.layer_ids.index(L)
        ids = np.asarray(m.engram.hashes(ref["token_history"], li)).reshape(-1)
        ranges = []
        for name in [k for k in ck.map if k.startswith(f"layers.{L}.engram.")]:
            meta, base, f = ck.meta(name)
            s0, e0 = meta["data_offsets"]
            if name.endswith(("engram.embed.weight", "engram.embed.scale")):
                width = {"F8_E4M3": 1, "F8_E8M0": 1, "BF16": 2, "F32": 4}[meta["dtype"]] * meta["shape"][1]
                for i in sorted(set(int(x) for x in ids)):
                    ranges.append((f, base + s0 + i * width, width))
            else:
                ranges.append((f, base + s0, e0 - s0))
        out[str(L)] = dict(ids=[int(x) for x in ids], ranges=ranges)
    Path(a.out).write_text(json.dumps(out))
    print({L: (len(v["ids"]), sum(r[2] for r in v["ranges"])) for L, v in out.items()})
    return 0


def cmd_engram_patch(a):
    """Tiny (reads only the listed byte ranges of the local shards): ranges -> one patch file."""
    import rtl_v41_fullshape_layer_campaign as LC
    want = json.loads(Path(a.snaps).read_text())
    blob = []
    for L, v in want.items():
        for f, off, n in v["ranges"]:
            with open(LC.HF / f, "rb") as fh:
                fh.seek(off)
                blob.append((f, off, fh.read(n)))
    Path(a.out).write_bytes(pickle.dumps(blob))
    print("ranges", len(blob), "bytes", sum(len(b[2]) for b in blob))
    return 0


def cmd_engram_apply(a):
    """On the compute host: write the patch into the sparse stand-in shards (same size, same header)."""
    import rtl_v41_fullshape_layer_campaign as LC
    blob = pickle.loads(Path(a.snaps).read_bytes())
    for f, off, data in blob:
        with open(LC.HF / f, "r+b") as fh:
            fh.seek(off)
            fh.write(data)
    print("applied", len(blob))
    return 0


# ======================================================================================================================
# record: results/rtl/dshbm_1m_allmeasured_20261004/local.json
# ======================================================================================================================
def model_ns(fn, n_keys=0):
    """The W19 composer's price of the step (ns on the chain, its domain applied), tools/w19_hbm_token_compose."""
    import w19_hbm_token_compose as WC
    op = dict(fn=fn, n=n_keys)
    ns, dom = WC.local_cycles(op, dict(n_keys=n_keys))
    return round(ns, 2), dom


def cmd_record(a):
    work = Path(a.work)
    sel = json.loads((work / "sel/select.json").read_text())
    idx = json.loads((work / "idx/idx.json").read_text())
    qu = json.loads((work / "quant/quant.json").read_text())
    su = json.loads(next((work / "su").glob("su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_local.json")).read_text())
    ef = json.loads((ROOT / "results/rtl/w19_expert_fetch.json").read_text())
    rows = {}

    def put(name, **kw):
        rows[name] = kw
    # index_q: SU RoPE chain (32 heads' tails + the weights scale), then one actquant FP4 QDQ over the 4,096 values
    for ch in su["chains"]:
        if ch["fn"] == "index_q":
            L = ch["layer"]
            q = next(r for r in qu["rows"] if r["node"] == f"{L}.idx_q_qdq")
            cyc = ch["cycles_end"] + q["cycles_one_instance"]
            put(f"{L}.index_q", fn="index_q", layer=L, cycles=cyc, clock_hz=SLOW, us=round(cyc / SLOW * 1e6, 4),
                domain="serial 0.9 GHz (SU + quantiser)", exact=bool(ch["exact"] and q["exact"]),
                n_checked=int(sum(c["n"] for c in ch["checks"])) + q["elements"],
                parts=dict(su_rope_and_weight_scale_cycles=ch["cycles_end"], fp4_qdq_cycles_one_instance=q["cycles_one_instance"]),
                source=f"SU N1024/M256 b4r5m4a3 dpi_beh chain {ch['chain']} + ot_hdc_actquant (fp4) quant.json",
                model_ns=model_ns("index_q")[0])
        if ch["fn"] == "engram_mix":
            L = ch["layer"]
            put(f"{L}.engram_mix", fn="engram_mix", layer=L, cycles=ch["cycles_end"], clock_hz=SLOW,
                us=round(ch["cycles_end"] / SLOW * 1e6, 4), domain="serial 0.9 GHz (SU incl. SFU EGATE side pipe)",
                exact=bool(ch["exact"]), n_checked=int(sum(c["n"] for c in ch["checks"])),
                source=f"SU N1024/M256 b4r5m4a3 dpi_beh chain {ch['chain']}", model_ns=model_ns("engram_mix")[0])
    for k, v in idx["results"].items():
        L = v["layer"]
        n = SCAN[L]
        beats = v["beats"]
        put(f"{k}.index_scores", fn="index_scores", layer=k, keys_die0=v["keys_die0"], cycles=v["cycles"],
            clock_hz=FAST, us=v["us_1p2GHz"], domain="fast 1.2 GHz (dedicated indexer array)", exact=v["exact"],
            n_checked=v["checked"], fixed_cycles=v["cycles"] - beats, ingest_keys_per_cycle=64,
            scaling="cycles = fixed + ceil(keys / 64): one 64-key beat a cycle (4,352 B of FP4 keys + scales a cycle "
                    "= 5.2 TB/s at 1.2 GHz, above the die's 4 x 1.0 TB/s HBM peak: the scan is HBM-stream-bound, "
                    "take max(stream, compute) + the fixed part)",
            masked_keys=v["masked"], cand_mask="inside (keep bit per key, -inf out), measured exact" if v["masked"] else None,
            source="ot_hdc_v41x_idx_array W11, NS2/NK4 x 8 slot windows", model_ns=model_ns("index_scores", n)[0])
    for name, r in sel["results"].items():
        L = r["layer"]
        fn = "cand_local" if name == "L20_cand" else "topk_local"
        put(f"L{L}.{fn}", fn=fn, layer=f"L{L}", keys_die0=r["keys_die0"], cycles=r["cycles"], clock_hz=FAST,
            us=r["us"], domain="fast 1.2 GHz (select unit, as the ROM prices it)", exact=r["exact"],
            ingest_cycles=r["ingest_cycles"], tail_after_last_input=r["tail"], overflow_replays=r["replays"],
            note="streaming filter at 64 scores a cycle = the scorer's output rate: on the chain only the tail follows "
                 "the last score when it ingests the scorer's stream directly (cycles = ingest + tail when run after)",
            unit=r["unit"], params=r["params"], model_ns=model_ns(fn, SCAN[L])[0])
    for r in qu["rows"]:
        if r["node"].endswith("idx_q_qdq"):
            continue
        put(f"{r['node']}", fn="quant", node=r["node"], elements=r["elements"], cycles=r["cycles_one_instance"],
            clock_hz=SLOW, us=r["us_one_instance"], domain="serial 0.9 GHz (one ot_hdc_actquant instance)",
            exact=r["exact"], n_checked=r["checked"] * 32, model_ns=round(40.6 * FAST / SLOW, 2))
    rt = ef["router_topk"]
    case = ef["cases"][0]
    put("router_top6", fn="route.top6", cycles=case["cycles_from_first_router_value"]["topk"], clock_hz=ef["clock_hz"],
        us=case["ns_from_first_router_value"]["topk"] / 1e3, domain="fast 1.2 GHz (ot_gpu_router_topk)",
        exact=rt["verdict"] == "pass", n_checked=rt["exact"],
        source="results/rtl/w19_expert_fetch.json router_topk (cited RTL: 24 beats of 16 scores + 23-cycle tail, "
               f"{rt['real_router_vectors']} real router vectors of the token + {rt['random_vectors']} random, exact)",
        model_ns=round((31.9 + 25.1) * FAST / SLOW, 2))
    unmeasured = [
        dict(fn="engram_fetch", why="an HBM table-row read (die 0 owns the hashed ids == 0 mod 96 of the layer's "
             "(n-1) x heads hashes), not a compute step; the ids depend only on the token history, so the read can "
             "issue at token start like the Engram gathers the W19 composer already takes off path (OFF_PATH_COLL "
             "'engram.'); its latency is an HBM first access (the HBM fork's measured service), not re-measured here"),
        dict(fn="cand_mask", why="not a separate unit: the indexer array applies the candidate keep bit per key "
             "(measured exact on L24, inside index_scores)")]
    rec = dict(schema="opentallas.dshbm-1m.allmeasured.local.v1", generated_utc=now(),
               scope="DS-V4.1 HBM accelerator, TP-96 die 0, position 1,048,575: the DU local steps the W19 model "
                     "prices, measured in RTL on the golden-checked executor's real operands",
               operands="tools/dshbm_baseline_measure.py execute --exec-layers L (L1, L2, L20, L24 alone, entering "
                        "from the W17 golden shard of the layer before; every layer region bit-exact)",
               rows=rows, unmeasured=unmeasured,
               pricing_guide=dict(
                   index_q="layers 2, 8, 14, 20, 24, 28, 32, 36: L2/L20/L24 rows (identical, 201 serial cycles: SU RoPE "
                           "60 + one-instance FP4 QDQ 141)",
                   index_scores="n 524,288 (L2, L8, L14): L2.index_scores; n 1,048,576: L20.index_scores (L20) and "
                                "L24.index_scores (L24/28/32/36, candidate mask applied in the array)",
                   topk_local="L2/L8: L2.topk_local; L14: L14.topk_local; L20: L20.topk_local; L24/28/32/36: "
                              "L24.topk_local (full masked stream)",
                   cand_local="L20 only", cand_mask="0 (inside index_scores)", engram_mix="L1 and L14: L1.engram_mix",
                   quant="hc_pre_norm / final_norm: *.attn.quant / *.ffn.quant (5,120, 173 cycles one instance); "
                         "q_norm_kv_row: q_quant (1,280, 53) and kv_row_qdq (512, 29) are independent (q and kv "
                         "chains): 53 on the chain if two instances, 82 if one",
                   route_top6="router_top6 (47 fast cycles, replaces the model's 31.9 + 25.1 ns)"),
               inputs={f"{d}/{f}": sha(work / d / f) for d, f in (("sel", "select.json"), ("idx", "idx.json"),
                                                                    ("quant", "quant.json"))},
               su_record=su.get("cases_sha256"), status="pass" if all(r.get("exact") for r in rows.values()) else "fail")
    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(rec, indent=1, default=float) + "\n")
    for k, r in rows.items():
        print(f"{k:28s} {r['cycles']:6} cyc {r['us']:.4f} us  model {r['model_ns']} ns  exact {r['exact']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=("select", "idx", "quant", "su-prep", "record", "engram-ids", "engram-patch",
                                     "engram-apply"))
    ap.add_argument("--layers", default="1")
    ap.add_argument("--gold", default=str(GOLD_DEFAULT))
    ap.add_argument("--work", default=None)
    ap.add_argument("--snaps", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--record", default=str(REC))
    a = ap.parse_args()
    return {"select": cmd_select, "record": cmd_record, "idx": cmd_idx, "quant": cmd_quant, "su-prep": cmd_su_prep,
            "engram-ids": cmd_engram_ids, "engram-patch": cmd_engram_patch,
            "engram-apply": cmd_engram_apply}[a.step](a)


if __name__ == "__main__":
    raise SystemExit(main())
