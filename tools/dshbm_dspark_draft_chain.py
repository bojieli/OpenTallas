#!/usr/bin/env python3
"""DS-V4.1 HBM accelerator: the DSpark DRAFT measured the way the ROM draft was (main dae91947c), and composed.

    HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_draft_chain.py golden    --out golden.pkl
    HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_draft_chain.py chain     --golden golden.pkl --out PART.json
    HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_draft_chain.py fullshape --out PART.json [--workdir DIR]
    python3 tools/dshbm_dspark_draft_chain.py compose --chain C.json --fullshape F.json --out composition.json

WHAT THE DRAFT IS (tools/hdc_golden_v41.py Model.draft; the ROM record's definition): embed [y, noise x 4], three
DSpark stages over the 5 block slots, the shared LM head on every slot (logits_i depend only on slot i's hidden
state), then a SERIAL 5-step sampling chain d_{i+1} = argmax(logits_i + markov(d_i)), d_0 = y (row i needs row i-1's
token).  The DSpark seed (main_proj + each stage's window row of the verified positions) and the commit are priced
separately, as the ROM's seed_commit term is.

CHAIN (exactness, reduced checkpoint, minimum component).  The HBM design's draft tail on its own RTL elements, closed
loop: the LM head pass on the SM element (rtl/gpu/ot_gpu_sm_v.sv, 5 MMA columns = the ctl's DHEAD; and once more one
column a step = the ROM's as-built structure), then per step the Markov head matvec of the embedding row of the
token the RTL argmax produced on the previous step (SM element, 1 column), then the bias add + full-vocabulary argmax
in rtl/gpu/dshbm/ot_dshbm_argmax.sv (ot_gpu_fadd RNE add, numpy.argmax semantics).  Python moves bytes only (the
embedding-row read and the logit/bias rows into the epilogue).  Checked bit for bit: every head logit and Markov
bias row against the golden's mv, every argmax against the golden's argmax(add(.)), and the drafts against
Model.draft.  Drafters: dspark (the RTL's own tokens feed the chain) and forced (the host forces the Markov inputs to
the golden AR continuation with one draft corrupted, as the ctl's cfg_force and the ROM campaign do).

FULLSHAPE (cycles, released weights, busiest SM of a TP-96 die).  The shapes the draft adds over the SM record:
the LM head with ONE column (a per-step head pass), every DSpark stage matvec at 5 columns on mtp.0's released
weights, the seed's wkv at 6 columns, and the argmax epilogue / 32-SM die merge / 96-die select.

COMPOSE.  Per die share at TP-96, from measured elements along the program (W19's composer: SM lines + drain, one
boundary per dependent SM op, dedicated units at their W11 prices, the routed experts as the drafter's measured
union), every collective of the draft COUNTED and priced per scenario with uarch_model's authoritative transports
(Tomahawk Ultra protocol for the accelerator), the head pass bounded by the die's HBM stream of its 13.8 MB head
share (4 stacks x 0.958 TB/s measured, minus the SMEM staging the idle window before it can prefill).  MTP is
recomputed at the third-party tau (uarch_model.TAU_DS; 4.159 self-measured superseded) for both sides with both drafts measured, ROM:HBM ratios, and the L1 / L2 ideas on HBM.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "build/models/deepseek-v4.1-flash-reduced-v2").exists():
    os.environ.setdefault("OPENTALLAS_BUILD", "/home/ubuntu/OpenTallas/build")
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np  # noqa: E402

F = np.float32
SCHEMA = "opentallas.rtl.dshbm_dspark_draft.v1"
REC = ROOT / "results/rtl/dshbm_dspark_draft_20261004"
RCHUNK = 256
JOBS = [16]               # simulations in flight per SM pass
CORRUPT_SLOT = 3          # forced drafter: the golden continuation with draft d_4 corrupted (ROM campaign: 2401 -> 2402)


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------ golden
def golden_draft_step():
    """Prefill the reduced vehicle's prompt (DSpark-seeded state), then the first draft at anchor q: the slots' normed
    head inputs, the golden logits, Markov tables and Model.draft's own output; plus the AR continuation."""
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    m = V.Model()
    prompt = [int(t) for t in V.prompt_and_expected()[0]]
    st = m.new_state(mtp=True)
    lg = None
    for p, t in enumerate(prompt):
        lg = m.forward_positions([t], p, st)[0]
    q, y = len(prompt) - 1, int(np.argmax(lg))
    B = m.dspark_block
    ids = [y] + [m.noise_id] * (B - 1)
    hs = [np.repeat(m.w["embed.weight"][t][None, :], m.hc, axis=0).astype(F) for t in ids]
    pres = [np.array([1, 0, 0, 0], dtype=F)[:m.hc] for _ in ids]
    for s in range(m.n_mtp):
        hs, pres = m.dspark_stage(m.L + s, hs, pres, q, st)
    Lf = m.L + m.n_mtp - 1
    xn = [V.rmsnorm_bf16(V.to_bf16(m.hc_pre(h, p)), m.lw(Lf, "norm.weight"), m.eps) for h, p in zip(hs, pres)]
    head = m.w["head.weight"]
    logits = [V.mv(head, x) for x in xn]
    emb, mhead = m.lw(Lf, "markov_head.embed.weight"), m.lw(Lf, "markov_head.head.weight")
    gout, glog = m.draft(y, q, st)
    # the reconstruction is the golden's draft, bit for bit
    chk, tok = [], y
    for i in range(B):
        row = V.add(logits[i], V.mv(mhead, emb[tok]))
        assert np.array_equal(V.bits(row), V.bits(glog[i])), i
        tok = int(np.argmax(row))
        chk.append(tok)
    assert chk == gout, (chk, gout)
    ar, _ = V.Model().generate(prompt, B + 2)
    return dict(prompt=prompt, q=q, y=y, B=B, xn=xn, logits=logits, head=np.asarray(head, dtype=F),
                emb=np.asarray(emb, dtype=F), mhead=np.asarray(mhead, dtype=F), draft=[int(t) for t in gout],
                ar=[int(t) for t in ar])


def cmd_golden(a):
    """The golden operands of the chain (needs the tokenizer for the reduced Engram tables: run where it is)."""
    import pickle
    g = golden_draft_step()
    a.out.write_bytes(pickle.dumps(g))
    print("golden", g["y"], g["draft"], g["ar"], sha(a.out))


# ------------------------------------------------------------------------------------------------------ RTL runs
def _sm():
    import dshbm_dspark_sm_campaign as SC
    import w19_sm_real_ops as WS
    return SC, WS


def sm_pass(tag, w, X, workdir, gold_rows):
    """One SM pass of a BF16 matvec over all rows (256 rows a simulation); returns the FP32 accumulators [NC][R], the
    mismatch count against the golden rows (the Model's own mv) and the per-simulation RTL meta."""
    SC, WS = _sm()
    R = w.shape[0]
    acc = [np.zeros(R, dtype=F) for _ in X]
    metas, mism = [], 0
    Path(workdir).mkdir(parents=True, exist_ok=True)

    def one(r0):
        r1 = min(R, r0 + RCHUNK)
        return r0, r1, WS.smv_real(f"{tag}:{r0}", "v41_bf16", w[r0:r1], X, workdir=str(workdir),
                                   sim_runner=SC.sim_runner)
    with ThreadPoolExecutor(JOBS[0]) as pool:
        res = list(pool.map(one, range(0, R, RCHUNK)))
    for r0, r1, (a, _, meta) in res:
        if a is None or meta.get("timeout") or meta.get("fault", 1) != 0:
            raise RuntimeError(f"{tag}:{r0} RTL failed: {meta}")
        for n in range(len(X)):
            acc[n][r0:r1] = a[n]
        metas.append(dict(rows=[r0, r1], cycles=meta.get("cycles_start_to_done"), lines=meta.get("lines"),
                          drain=meta.get("drain_last_line_to_last_result")))
    for n, g in enumerate(gold_rows):
        mism += int(np.sum(acc[n].view(np.uint32) != np.asarray(g, dtype=F).view(np.uint32)))
    return acc, mism, metas


def argmax_rtl(rows, biases, nv, workdir, label):
    import dshbm_dspark_rtl_campaign as RC
    os.makedirs(workdir, exist_ok=True)
    return RC.run_argmax(rows, biases, nv, 8, workdir, label)


def cmd_chain(a):
    import pickle
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    g = pickle.loads(Path(a.golden).read_bytes())
    B = g["B"]
    wd = Path(a.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    head = np.asarray(g["head"], dtype=F)
    mhead = np.asarray(g["mhead"], dtype=F)
    nv = head.shape[0]
    # the ctl's DHEAD: one pass, 5 MMA columns
    h5, h5_mism, h5_meta = sm_pass("dhead5", head, g["xn"], wd / "dhead5", g["logits"])
    # the ROM's as-built structure: one head pass a step, one column each (exactness of the 1-column pass)
    def h1pass(i):
        acc, mi, meta = sm_pass(f"dhead1_{i}", head, [g["xn"][i]], wd / f"dhead1_{i}", [g["logits"][i]])
        return dict(slot=i, mismatches=mi, equal_to_5col=bool(np.array_equal(acc[0].view(np.uint32),
                                                                              h5[i].view(np.uint32))), sims=meta)
    vocab = nv
    forced = list(g["ar"][1:B + 1])
    forced[CORRUPT_SLOT] = (forced[CORRUPT_SLOT] + 1) % vocab
    def run_drafter(name):
        tok, steps, out = g["y"], [], []
        for i in range(B):
            e = np.asarray(g["emb"][tok], dtype=F)                       # the embedding row of the previous token
            gbias = V.mv(mhead, e)
            bias, bm, bmeta = sm_pass(f"{name}_mk{i}", mhead, [e], wd / f"{name}_mk{i}", [gbias])
            got = argmax_rtl([h5[i]], [bias[0]], nv, str(wd / "am"), f"{name}{i}")[0]
            want = int(np.argmax(V.add(g["logits"][i], gbias)))
            steps.append(dict(step=i, input_token=int(tok), markov_bias_mismatches=bm, argmax_rtl=got["idx"],
                              argmax_golden=want, exact=bm == 0 and got["idx"] == want and got["fault"] == 0,
                              argmax_cycles_first_beat_to_result=got["cycles"], argmax_fault=got["fault"],
                              markov_sims=bmeta))
            out.append(int(got["idx"]))
            tok = int(got["idx"]) if name == "dspark" else forced[i]
        rec = dict(drafter=name, steps=steps, chain_argmax=out)
        if name == "dspark":
            rec.update(drafts_rtl=out, drafts_golden=g["draft"], drafts_equal_golden=out == g["draft"])
        else:
            rec.update(forced_inputs=[g["y"]] + forced[:B - 1], forced_drafts=forced, ar_continuation=g["ar"],
                       corrupted_slot=CORRUPT_SLOT)
        rec["exact"] = all(s["exact"] for s in steps) and rec.get("drafts_equal_golden", True)
        return rec
    with ThreadPoolExecutor(B + 2) as pool:
        fh1 = [pool.submit(h1pass, i) for i in range(B)]
        fdr = {n: pool.submit(run_drafter, n) for n in ("dspark", "forced")}
        h1 = [f.result() for f in fh1]
        drafters = {n: f.result() for n, f in fdr.items()}
    passed = (h5_mism == 0 and all(x["mismatches"] == 0 and x["equal_to_5col"] for x in h1)
              and all(d["exact"] for d in drafters.values()))
    return dict(part="chain", status="pass" if passed else "fail", vehicle="reduced-v2 checkpoint (dim %d, vocab %d, "
                "markov rank %d), prompt %s, anchor q=%d, y=%d" % (head.shape[1], nv, mhead.shape[1], g["prompt"],
                                                                     g["q"], g["y"]),
                dhead5=dict(mismatches=h5_mism, sims=h5_meta), dhead1=h1, drafters=drafters), passed


def cmd_fullshape(a):
    import hdc_golden as G
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    SC, WS = _sm()
    ck = LC.Checkpoint()
    rng = np.random.default_rng(20261004)
    TP, NSM = 96, 32
    wd = Path(a.workdir)
    wd.mkdir(parents=True, exist_ok=True)

    def busiest(R):
        die = -(-R // TP)
        return -(-die // NSM)

    def bf16(name):
        v = ck.get(name)
        return np.asarray(v, dtype=F)

    def q8(name):
        codes = ck.get(name)
        sc = ck.get(name[:-len(".weight")] + ".scale")
        return V._blocked(codes, sc, name)

    jobs = []
    wh = bf16("head.weight")
    R = busiest(wh.shape[0])
    jobs.append(("lm_head_1slot", "v41_bf16", wh[:R], [G.to_bf16(rng.standard_normal(wh.shape[1]).astype(F))],
                 "real weights, synthetic BF16 activation", None))
    # the DSpark stage matvecs at 5 columns (W19 program shapes: rows = the busiest SM's share)
    stage = [("wq_a", "mtp.0.attn.wq_a.weight", 1), ("wkv", "mtp.0.attn.wkv.weight", 1),
             ("wq_b", "mtp.0.attn.wq_b.weight", 16), ("wo_b", "mtp.0.attn.wo_b.weight", 2),
             ("expert_w1", "mtp.0.ffn.experts.0.w1.weight", 1), ("expert_w2", "mtp.0.ffn.experts.0.w2.weight", 2)]
    for tag, name, Rs in stage:
        w = q8(name)
        fmt = "v41_fp4" if ck.raw(name)[1] == "I8" else "v41_fp8"
        X = [G.to_bf16(rng.standard_normal(w.q.shape[1]).astype(F)) for _ in range(5)]
        jobs.append((f"stage_{tag}_5col", fmt, V.Q8(w.q[:Rs], w.e[:Rs]), X, "real mtp.0 weights, synthetic BF16 "
                     "activations", None))
    gate = bf16("mtp.0.ffn.gate.weight")
    jobs.append(("stage_router_gate_5col", "v41_bf16", gate[:1], [G.to_bf16(rng.standard_normal(gate.shape[1])
                                                                            .astype(F)) for _ in range(5)],
                 "real mtp.0 weights, synthetic BF16 activations", None))
    woa = q8("mtp.0.attn.wo_a.weight")
    woa_d = G.to_bf16(woa.dense())[:32, :512]
    jobs.append(("stage_wo_a_5col", "v41_bf16", woa_d, [G.to_bf16(rng.standard_normal(512).astype(F))
                                                        for _ in range(5)],
                 "real mtp.0 wo_a (dense BF16, the die's 512-column head group), synthetic BF16 activations", None))
    wkv = q8("mtp.0.attn.wkv.weight")
    jobs.append(("seed_wkv_6col", "v41_fp8", V.Q8(wkv.q[:1], wkv.e[:1]),
                 [G.to_bf16(rng.standard_normal(wkv.q.shape[1]).astype(F)) for _ in range(6)],
                 "real mtp.0 weights, synthetic BF16 activations (the seed's window rows of 6 verified positions)",
                 None))

    def one(j):
        tag, fmt, w, X, src, _ = j
        acc, gold, meta = WS.smv_real(tag, fmt, w, X, workdir=str(wd), sim_runner=SC.sim_runner)
        mism = sum(int(np.sum(G.bits(x) != G.bits(g))) + int(np.isnan(x).sum()) for x, g in zip(acc, gold))
        K = np.asarray(w).shape[1] if fmt == "v41_bf16" else w.q.shape[1]
        Rr = np.asarray(w).shape[0] if fmt == "v41_bf16" else w.q.shape[0]
        return dict(case=tag, fmt=fmt, K=int(K), sm_rows=int(Rr), cols=len(X), operands=src,
                    accumulator_mismatches=mism, exact=mism == 0 and meta.get("fault", 1) == 0 and not meta.get("timeout"),
                    rtl=meta)
    with ThreadPoolExecutor(len(jobs)) as pool:
        cases = list(pool.map(one, jobs))
    for c in cases:
        print(c["case"], c["fmt"], "K", c["K"], "R", c["sm_rows"], "cols", c["cols"],
              "EXACT" if c["exact"] else "MISMATCH", "cycles", c["rtl"].get("cycles_start_to_done"),
              "lines", c["rtl"].get("lines"), flush=True)
    # argmax epilogue / merges at full shape
    timing = {}
    for label, nv, bias in (("sm_epilogue_43_bias", 43, True), ("die_merge_32", 32, False),
                            ("cross_die_select_96", 96, False)):
        rs = [(rng.standard_normal(nv) * 3).astype(F) for _ in range(4)]
        bs = [(rng.standard_normal(nv) * 3).astype(F) for _ in range(4)] if bias else None
        got = argmax_rtl(rs, bs, nv, str(wd / "am"), label)
        ok = all(x["idx"] == int(np.argmax(G.add(r, b) if bias else r)) for r, b, x in zip(rs, bs or [None] * 4, got))
        timing[label] = dict(values=nv, lanes=8, bias=bias, cycles_first_beat_to_result=got[0]["cycles"], exact=ok)
    passed = all(c["exact"] for c in cases) and all(t["exact"] for t in timing.values())
    return dict(part="fullshape", status="pass" if passed else "fail", checkpoint=str(LC.HF), cases=cases,
                argmax_timing=timing), passed


# ------------------------------------------------------------------------------------------------------ compose
F_FAST = 1.2e9
HEAD_ROWS_DIE = math.ceil(129280 / 96)
HEAD_BYTES_DIE = HEAD_ROWS_DIE * 5120 * 2                     # BF16 head share a die streams per pass
MARKOV_BYTES_DIE = HEAD_ROWS_DIE * 256 * 2                    # resident in SMEM across the 5 steps
STACK_BPS = 0.958e12                                          # MEASURED sustained per stack (refresh-aware controller,
                                                              # hbm_accelerator ladder Q_STACK_TBPS_MEASURED)
STACKS_DIE = 4
STAGING_B_DIE = 32 * 128 * 1024                               # uarch_model hbm_gpu V4.1 staging_kb_per_sm 128 x 32 SMs
CTL_CYC_STEP = 60                                             # dshbm ctl loop cycles a step outside engine commands
                                                              # (dshbm_dspark_rtl REPLAY: 840-1,900 a run, ~60 a step)


def transport_us(ops, scen, um):
    """The draft's collective TRANSPORT (us) under one switch scenario, priced exactly as uarch_model prices the W19
    pass's collectives (w19_transport_us): ops = [(kind, bytes x P, P, op)]."""
    _, coll, W = um.w19_collective_ops()
    hz = coll["hz"]
    tot = 0.0
    for kind, nbytes, P, op in ops:
        if scen in um.TU_SCEN:
            tot += um.tu_transport_us(kind, nbytes, scen)
            continue
        us, _ = W.prod_us(op, coll, P)
        if scen != "w15":
            k = "ar" if kind == "all_reduce" else "ag"
            fixed = (coll["ar"]["fixed_cycles"] if k == "ar" else coll["ag"]["fixed_cycles"]) / hz * 1e6
            us += um.hbm_switch_collective_us(scen, k, "board") - fixed
        tot += us
    return tot


def cmd_compose(a):
    import uarch_model as um
    import v41_hbm_speculation_methods as SPM
    from hbm_accelerator_model import _load_study
    ch = json.loads(Path(a.chain).read_text())
    fs = json.loads(Path(a.fullshape).read_text())
    smf = json.loads((ROOT / "results/rtl/dshbm_dspark_rtl_20261003/sm_fullshape.json").read_text())
    assert ch["status"] == "pass" and fs["status"] == "pass" and smf["status"] == "pass"
    meas = {c["case"]: c["rtl"] for c in fs["cases"] + smf["cases"]}
    am = fs["argmax_timing"]
    cyc = lambda r: r["lines"] + r["drain_last_line_to_last_result"]                     # noqa: E731  composer rule
    us = lambda c: c / F_FAST * 1e6                                                       # noqa: E731
    w = SPM.W19()
    C = w.C
    # the draft's stage SM shapes at 5 columns, MEASURED here, override the 1-column record entries
    over = {("v41_fp8", 5120, 1): "stage_wq_a_5col", ("v41_fp8", 1280, 16): "stage_wq_b_5col",
            ("v41_fp8", 8192, 2): "stage_wo_b_5col", ("v41_fp4", 5120, 1): "stage_expert_w1_5col",
            ("v41_fp4", 2304, 2): "stage_expert_w2_5col", ("v41_bf16", 5120, 1): "stage_router_gate_5col",
            ("v41_bf16", 512, 32): "stage_wo_a_5col"}
    sm_1col = {k: dict(v) for k, v in w.sm.rows.items()}
    for key, case in over.items():
        r = meas[case]
        w.sm.rows[key] = dict(lines=r["lines"], drain=r["drain_last_line_to_last_result"],
                              start_to_done=r["cycles_start_to_done"], exact=True)
    st, _, _ = w.draft_programs()
    # stage 0's main_proj / main_x gather / main_norm are the SEED's (Model.dspark_seed), not the draft's
    seed_ops = st["layers"][0]["ops"][:3]
    st["layers"][0]["ops"] = st["layers"][0]["ops"][3:]
    uj = json.loads((SPM.REC_DIR / "router_union.json").read_text())
    u_stage = uj["drafter"]["union_per_stage"]
    stg = w.run(st, SPM.BLOCK, {f"dspark{s}": u_stage[s] for s in range(3)})
    stage_ops = [(op["kind"], SPM.BLOCK * op["bytes"], SPM.BLOCK, op) for lay in st["layers"] for op in lay["ops"]
                 if op["kind"] in ("all_gather", "all_reduce", "topk_merge", "kv_gather")]
    stage_coll_w15 = stg["parts_us"]["collective"]
    # per-stage boundaries the composer charged (one per dependent SM-op run)
    stage_parts = {k: v for k, v in stg["parts_us"].items() if k != "collective"}
    # ---- head: one 5-column pass (the ctl's DHEAD) vs a 1-column pass a step; the die's HBM stream bound ----
    fetch_us = w.fetch_us
    bw = STACKS_DIE * STACK_BPS
    stream_us = HEAD_BYTES_DIE / bw * 1e6
    staging = STAGING_B_DIE - MARKOV_BYTES_DIE
    final_norm_us = C.local_cycles(dict(fn="final_norm"), w.m())[0] / 1e3 * C.LOCAL_REPEAT(SPM.BLOCK)
    head5_sm, head1_sm = us(cyc(meas["lm_head_5slots"])), us(cyc(meas["lm_head_1slot"]))
    hb = C.BARRIER_CYC / F_FAST * 1e6
    merge_op = dict(kind="topk_merge", what="argmax", k=1, elems=96, bytes=768, tag="argmax merge")
    tu_merge = um.tu_transport_us("topk_merge", 768)
    # the chain step (as built: Markov SM -> fused bias+argmax epilogue -> die merge -> 96-die gather + select)
    mk_sm = us(cyc(meas["markov_head"]))
    am_us = us(am["sm_epilogue_43_bias"]["cycles_first_beat_to_result"] + am["die_merge_32"]["cycles_first_beat_to_result"])
    sel_us = us(am["cross_die_select_96"]["cycles_first_beat_to_result"])

    def head_pass(sm_us, idle_us):
        """max(SM, the die's head stream minus what the staging prefetched in the idle window before the pass)."""
        pre = min(staging, bw * idle_us * 1e-6)
        return max(sm_us, (HEAD_BYTES_DIE - pre) / bw * 1e6), pre
    # idle window before DHEAD: stage 2's tail after its last SM op (moe_sum, ffn_out gather, hc_post) + final_norm
    tail_local = sum(C.local_cycles(dict(fn=f), w.m())[0] for f in ("moe_sum", "hc_post")) / 1e3 * C.LOCAL_REPEAT(5)
    ffn_gather_tu = um.tu_transport_us("all_gather", 5 * 10240)
    h5_pass, h5_pre = head_pass(head5_sm, tail_local + ffn_gather_tu + final_norm_us)
    step_core = fetch_us + mk_sm + hb + am_us + sel_us                 # + merge transport (per scenario)
    step_core_tu = step_core + tu_merge
    h1_pass, h1_pre = head_pass(head1_sm, step_core_tu)             # the previous step's window refills the staging
    # ---- seed (the ROM's seed_commit term): main_proj 6 cols, main_x gather, main_norm, 3 stages' wkv rows ----
    seed_sm = us(cyc(meas["main_proj_6pos"])) + 3 * us(cyc(meas["seed_wkv_6col"]))
    seed_local = (C.local_cycles(dict(fn="hc_pre_norm"), w.m())[0]
                  + 3 * C.local_cycles(dict(fn="q_norm_kv_row"), w.m())[0]) / 1e3 * C.LOCAL_REPEAT(6)
    seed_bar = 4 * hb
    commit_us = us(CTL_CYC_STEP)
    seed_ops_coll = [(op["kind"], 6 * op["bytes"], 6, op) for op in seed_ops if op["kind"] == "all_gather"]

    def draft_variant(per_step_head):
        parts = dict(sm=stage_parts["sm"] + h5_pass if not per_step_head else stage_parts["sm"],
                     barrier=stage_parts["barrier"] + hb, local=stage_parts["local"] + final_norm_us,
                     fetch=stage_parts["fetch"] + fetch_us)                         # + y's embedding row
        steps = SPM.BLOCK
        parts["sm"] += steps * mk_sm + (steps * h1_pass if per_step_head else 0.0)
        parts["barrier"] += steps * hb * (2 if per_step_head else 1)
        parts["local"] += steps * (am_us + sel_us)
        parts["fetch"] += steps * fetch_us
        ops = stage_ops + [("topk_merge", 768, 1, merge_op)] * steps
        return dict(parts_us={k: round(v, 3) for k, v in parts.items()}, collectives=ops)
    variants = dict(as_built=draft_variant(False), per_step_head=draft_variant(True))
    seed = dict(parts_us=dict(sm=round(seed_sm, 3), local=round(seed_local, 3), barrier=round(seed_bar, 3),
                              commit=round(commit_us, 3)), collectives=seed_ops_coll)
    # ---- compose with the authoritative designs / scenarios ----
    m, _, ds, _ = _load_study(ROOT)
    n = m.W19_COLL_COUNT
    rel = (m.W19_BOUNDARY_CYC - m.W19_BARRIER_RELEASE_CYC) / m.W19_BOUNDARY_CYC
    hw_b = m.W19_BOUNDARY_CYC / m.F_FAST * 1e6
    auth = um.hbm_switch_latency_authoritative()
    prim = [r for r in auth["rows"] if r["primary"]]
    rom = auth["rom"]
    l12 = json.loads((ROOT / um.DSROM_DRAFT_L1L2).read_text())["result"]["levers"]
    rom_dft = json.loads((ROOT / um.DSROM_DRAFT_MEASURED).read_text())["full_shape"]["ctx"]
    g_new = um.GPU["barrier_ns_grid_h100_measured"]
    rungs = {r: s for r, s, _ in m.ds_rungs(1, include_conditional=False)}

    def draft_us(v, design, scen, part="draft"):
        d = variants[v] if part == "draft" else seed
        p = dict(d["parts_us"])
        tr = transport_us(d["collectives"], scen, um)
        if design.startswith("accelerator_firm") and scen == "w15":
            tr *= 1 - rungs["R3a"] / m.W19_AR["collective"]
        if design.startswith("accelerator"):
            p["barrier"] = p["barrier"] * rel if design == "accelerator_firm_switch" else p["barrier"]
        if design == "gpu_faithful_r0":
            p["barrier"] = p["barrier"] + p["barrier"] / hw_b * (g_new * 1e-3 - hw_b)
        return sum(p.values()) + tr, tr
    old_draft = {}
    rows = []
    ctxk = {"1M": "1048576", "200K": "200000"}
    for r in prim:
        dsg, sc, ctx = r["design"], r["scenario"], r["ctx"]
        if dsg == "gpu_faithful_r0_v100_superseded":
            continue
        k = 1.0 if ctx == "1M" else m.CTX_200K_RATIO
        # the old step = verify(P=6) part + the model draft; recover verify by removing the model draft exactly
        dd = auth["designs"][dsg] if dsg != "accelerator_firm_switch" else \
            auth["designs"][dsg]["replaced" if sc != "w15" else "w15"]
        d6 = r["mtp_step_us"] - dd["ver"] * k - dd["draft"] * k
        n_draft = auth["collective_counts"]["draft_assumed"]
        d1 = r["ar_us"] - dd["ar"] * k
        old_dr = dd["draft"] * k + d1 * n_draft / n["total"]
        ver = r["mtp_step_us"] - old_dr
        old_draft[(dsg, sc, ctx)] = old_dr
        out = dict(ctx=ctx, design=dsg, scenario=sc, authoritative_default=r["authoritative_default"],
                   ar_tok_s=r["ar_tok_s"], verify_p6_us=round(ver, 2), model_draft_us=round(old_dr, 2),
                   old_mtp_tok_s=r["mtp_tok_s"])
        seed_us, seed_tr = draft_us("as_built", dsg, sc, "seed")
        out["seed_commit_us"] = round(seed_us, 3)
        rk = ctxk[ctx]
        romv = dict(ar=rom[ctx]["ar_tok_s"], as_built=rom[ctx]["mtp_as_built_tok_s"],
                    l1=rom[ctx]["mtp_fused_head_tok_s"], l1l2=rom[ctx]["mtp_l1l2_rom_read_k5_tok_s"])
        for v in variants:
            dr, tr = draft_us(v, dsg, sc)
            step = ver + dr + seed_us
            mtp = um.TAU_DS * 1e6 / step
            out[v] = dict(draft_us=round(dr, 2), draft_transport_us=round(tr, 3), step_us=round(step, 2),
                          mtp_tok_s=round(mtp, 1), vs_model_draft=round(mtp / r["mtp_tok_s"] - 1, 4),
                          rom_over_hbm_mtp=dict(rom_as_built=round(romv["as_built"] / mtp, 3),
                                                rom_l1=round(romv["l1"] / mtp, 3),
                                                rom_l1l2_expected=round(romv["l1l2"] / mtp, 3)))
            out[v]["draft_over_ar"] = round(dr / r["ar_us"], 4)
        out["rom_over_hbm_ar"] = r["rom_over_hbm_ar"]
        rows.append(out)
    # ---- L1 / L2 on HBM (report, not built) ----
    l1l2 = dict(
        L1_fused_bias_argmax=dict(status="ALREADY IN the HBM as-built draft",
                                  basis="rtl/gpu/dshbm/ot_dshbm_argmax.sv is the SM epilogue: the Markov bias add "
                                        "(ot_gpu_fadd) and the argmax run on the epilogue registers, no SMEM round "
                                        "trip; the as-built chain step already prices it (%.1f ns epilogue + die merge)"
                                        % (am_us * 1e3), gain_us=0.0),
        L2_batched_head=dict(status="ALREADY IN the HBM as-built draft (the ctl's DHEAD: one 5-column pass)",
                             per_step_head_minus_batched_us=round(variants["per_step_head"]["parts_us"]["sm"]
                                                                  - variants["as_built"]["parts_us"]["sm"]
                                                                  + variants["per_step_head"]["parts_us"]["barrier"]
                                                                  - variants["as_built"]["parts_us"]["barrier"], 3),
                             basis="the 5 slot logit rows do not depend on the chain's tokens; the HBM design "
                                   "already issues them as one weight pass (lines independent of columns: 1 col %d "
                                   "lines, 5 cols %d)" % (meas["lm_head_1slot"]["lines"], meas["lm_head_5slots"]["lines"])),
        remaining_chain=dict(per_step_us_tu=round(step_core_tu, 3),
                             merge_transport_share=round(tu_merge / step_core_tu, 3),
                             note="what is left on the HBM chain is the cross-die argmax merge (one Tomahawk crossing "
                                  "+ tail a step); no further L1/L2-class lever applies"))
    res = dict(
        definition="draft = embed (y's row) + 3 DSpark stages over 5 slots + LM head + SERIAL 5-step chain "
                   "(Markov head matvec of d_i's embedding, bias add + full-vocab argmax, die merge, 96-die gather + "
                   "select); seed_commit (main_proj 6 cols, main_x gather, main_norm, 3 stages' wkv window rows, ctl "
                   "commit) separate, as the ROM record's seed_commit; step = verify(P=6) + draft + seed_commit",
        elements=dict(
            stage_sm_5col_measured={k[0] + f" K{k[1]} R{k[2]}": dict(case=c, lines=meas[c]["lines"],
                                                                    drain=meas[c]["drain_last_line_to_last_result"],
                                                                    start_to_done=meas[c]["cycles_start_to_done"],
                                                                    record_1col=sm_1col.get(k))
                                    for k, c in over.items()},
            head=dict(lm_head_5col_cycles=cyc(meas["lm_head_5slots"]), lm_head_1col_cycles=cyc(meas["lm_head_1slot"]),
                      start_to_done_5col=meas["lm_head_5slots"]["cycles_start_to_done"],
                      start_to_done_1col=meas["lm_head_1slot"]["cycles_start_to_done"],
                      head_bytes_die=HEAD_BYTES_DIE, die_stream_TBps=bw / 1e12, stream_us_no_staging=round(stream_us, 3),
                      staging_B_die=staging, pass_5col_us=round(h5_pass, 3), prefetched_B_5col=round(h5_pre),
                      pass_1col_us=round(h1_pass, 3), prefetched_B_1col=round(h1_pre),
                      bound="HBM stream" if h5_pass > head5_sm else "SM lines",
                      basis="head weights live in HBM (the DS HBM design keeps every weight in HBM; L2 4 x 2 MB "
                            "is bypassed by weights; SMEM staging 128 KB a SM) and stream every pass"),
            chain_step=dict(fetch_us=round(fetch_us, 4), markov_sm_cycles=cyc(meas["markov_head"]),
                            boundary_cycles=C.BARRIER_CYC,
                            argmax_epilogue_cycles=am["sm_epilogue_43_bias"]["cycles_first_beat_to_result"],
                            die_merge_cycles=am["die_merge_32"]["cycles_first_beat_to_result"],
                            cross_die_select_cycles=am["cross_die_select_96"]["cycles_first_beat_to_result"],
                            merge_transport_tu_us=round(tu_merge, 4), step_us_tu=round(step_core_tu, 4)),
            stages=dict(parts_us_wo_transport=stage_parts, w15_collective_us=stage_coll_w15,
                        union_per_stage=u_stage, collectives=len(stage_ops), flags=stg["flags"]),
            seed=dict(parts_us=seed["parts_us"], collectives=len(seed_ops_coll))),
        collective_count=dict(draft=len(variants["as_built"]["collectives"]), stages=len(stage_ops),
                              chain_merges=SPM.BLOCK, seed=len(seed_ops_coll), model_assumed=auth["collective_counts"]["draft_assumed"]),
        variants={k: dict(parts_us_wo_transport=v["parts_us"],
                          transport_us={sc: round(transport_us(v["collectives"], sc, um), 3)
                                        for sc in ("w15", "tomahawk_ultra_protocol", "nvls_measured", "gpu_fenced")})
                  for k, v in variants.items()},
        rows=rows, hbm_l1_l2=l1l2,
        rom=dict(rom_draft_us={c: dict(as_built=rom_dft[rk]["as_built_chain"]["draft_us"],
                                       fused_head=rom_dft[rk]["fused_head"]["draft_us"],
                                       seed_commit=rom_dft[rk]["seed_commit_us"]) for c, rk in ctxk.items()},
                 l1l2_expected_k5={c: l12["l1l2/rom_read/k5"]["ctx"][rk]["occupancy"]["mtp_tok_s"] for c, rk in ctxk.items()},
                 values=rom),
        tau=um.TAU_DS, tau_src=um.TAU_DS_SRC)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("part", choices=("golden", "chain", "fullshape", "compose"))
    ap.add_argument("--golden", type=Path, help="chain: the golden operands (the golden part's output)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workdir", default="/tmp/claude-1000/dshbm-draft/work")
    ap.add_argument("--chain", type=Path)
    ap.add_argument("--fullshape", type=Path)
    a = ap.parse_args()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() \
        or os.environ.get("OT_SOURCE_COMMIT", "")
    stamp = dict(schema=SCHEMA, source_commit=head,
                 generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    if a.part == "golden":
        cmd_golden(a)
        return 0
    if a.part == "compose":
        rec = cmd_compose(a)
        rec.update(stamp, inputs={str(p): sha(p) for p in (a.chain, a.fullshape)},
                   source_sha256={s: sha(ROOT / s) for s in ("tools/dshbm_dspark_draft_chain.py", "tools/uarch_model.py",
                                                             "tools/v41_hbm_speculation_methods.py")})
        a.out.write_text(json.dumps(rec, indent=1) + "\n")
        return 0
    rec, passed = cmd_chain(a) if a.part == "chain" else cmd_fullshape(a)
    if a.part == "chain":
        rec["golden_operands_sha256"] = sha(a.golden)
    SC, _ = _sm()
    srcs = sorted(set(SC.SMV_SRC + ["rtl/gpu/dshbm/ot_dshbm_argmax.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/test/tb_dshbm_argmax.sv",
                                    "tools/dshbm_dspark_draft_chain.py", "tools/dshbm_dspark_sm_campaign.py",
                                    "tools/dshbm_dspark_rtl_campaign.py", "tools/w19_sm_real_ops.py",
                                    "tools/rtl_gpu_sm_exact.py", "tools/hdc_golden_v41.py"]))
    sim = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0]
    rec.update(stamp, simulator=sim, source_sha256={s: sha(ROOT / s) for s in srcs})
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print("PASS" if passed else "FAIL", a.out)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
