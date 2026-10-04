#!/usr/bin/env python3
"""Exact local-chain levers of the DeepSeek-V4.1 HBM accelerator at 1M (position 1,048,575), measured on the same
stream-unit vehicle and the same captured operands as the measured baseline (tools/dshbm_baseline_measure.py,
results/rtl/dshbm_baseline_measured_20261004: ot_hdc_v41x_vec N 1,024 / M 256, B4 R5 MLAT4 ALAT3, DPI FP stand-ins).
The ROM accelerator's exact implementation levers, applied to the HBM chains (golden rounding and reduction order
unchanged: every op computes the same elements from the same operands, only issue order / operand path changes):

  il   compiler scheduling (dataflow level 4): independent sub-chains issue interleaved instead of back to back
       (q_norm and kv_norm of q_norm_kv_row: their sums of squares, rsqrts and scalings overlap), and the kv row's
       copy op is designed out (the scaling writes the output row directly; the RoPE rotates its tail in place);
  kr   lane-local fusion (dataflow level 1, the ROM's W11 `_kr` lane-register build ot_hdc_v41x_vec_kr.sv, the
       pass tools/w11_su_fuse.fuse_bench): an op that consumes the previous op's elements on the same lanes reads
       them from the lane registers instead of a vector-memory round trip (hc_pre_norm, hc_post, ...).
Each variant is measured in RTL on every chain (1 position and the 6 verify positions, op-major), checked word for
word against the executor's (golden-checked) values, and recomposed with tools/dshbm_baseline_measure.compose_program
(Tomahawk-protocol collectives, the authoritative switch scenario).

    python3 tools/dshbm_chain_levers.py prep --cases DIR/su_cases_v2.pkl --out DIR      # il / il+kr case sets
    python3 tools/dshbm_chain_levers.py run --out DIR --work W --cases su_cases_v2_il.pkl [--kr 40] [--n --m --fp]
    python3 tools/dshbm_chain_levers.py compose --base results/rtl/dshbm_baseline_measured_20261004 \
        --variants name=su1.json,su6.json ... --record results/rtl/dshbm_local_chains_20261004/levers.json
"""
from __future__ import annotations

import argparse
import copy
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dshbm_baseline_measure as DM  # noqa: E402

KR_DEFAULT = 40                      # the ROM's fused build (results/rtl/dsrom_system_rtl_20261003/levers/su_kr.json)


# ---- il: scheduling + copy elimination ----------------------------------------------------------------------------
def il_q_norm_kv_row(ops):
    """One position's 8 ops [q_ss, q_rs, q_mul, kv_ss, kv_rs, kv_mul, copy, rope] -> 7 ops
    [q_ss, kv_ss, q_rs, kv_rs, q_mul, kv_mul -> out, rope in place on out's tail]."""
    assert len(ops) == 8, len(ops)
    q_ss, q_rs, q_mul, kv_ss, kv_rs, kv_mul, cp, rope = (dict(o) for o in ops)
    assert cp["nin"] + rope["nin"] == kv_mul["nin"] and cp["abase"] == kv_mul["obase"]
    assert rope["abase"] == kv_mul["obase"] + cp["nin"] and rope["obase"] == cp["obase"] + cp["nin"]
    kv_mul["obase"] = cp["obase"]                     # the scaled row lands in the output row
    rope["abase"] = rope["obase"]                     # the tail rotates in place (as attend's inverse RoPE does)
    return [q_ss, kv_ss, q_rs, kv_rs, q_mul, kv_mul, rope]


IL = {"q_norm_kv_row": il_q_norm_kv_row}


def dr_hc_post(ops):
    """Drop the sum of squares hc_post's last op chains onto the new residual: no stream-unit consumer reads it --
    the mixes' projection engine (rtl/hdc/v41x/ot_hdc_v41x_hcp.sv, cmd_scale = 1) computes ss = csum(flat * flat)
    itself, concurrently with its rows (Model.hc_mixes), so the reduction tail leaves hc_post's chain."""
    ops = [dict(o) for o in ops]
    last = ops[-1]
    assert last["red"] and last["redsq"], last
    last.update(red=0, redsq=0, redtree=0, rbase=0)
    return ops


def attend_tail_case(c, VC):
    """The attention chain's part AFTER the tile's p.v (normalise by the denominator, inverse RoPE), as its own case:
    p.v rows and the denominator (the reference's value of the full chain) preloaded.  The max / exp (+ the sum,
    sink and denominator, which run under the tile's p.v phase) stay in the full chain's measurement."""
    import numpy as np
    vm = np.zeros(1 << VC.VMA, dtype=np.uint32)
    for ad, v in c["init"]:
        vm[ad:ad + len(v)] = np.asarray(v, dtype=DM.F).view(np.uint32)
    mem0 = VC.Mem(vm, np.zeros(1 << VC.KVA, dtype=np.uint32), np.stack([c["cr_lo"], c["cr_hi"]], axis=1),
                  np.zeros(1 << VC.WRA, dtype=np.uint16))
    mref = VC.schedule(c["ops"], mem0, DM.SU_N, DM.SU_M)[0]
    t = copy.deepcopy(c)
    t["ops"] = per_position(c, lambda ops: [dict(o) for o in ops[-2:]])
    dens = sorted({o["bbase"] for o in t["ops"] if o["m1"] == 4})          # M1_DIVB: the broadcast denominator
    t["init"] = list(c["init"]) + [(d, mref.vm[d:d + 1].view(DM.F).copy()) for d in dens]
    t["checks"] = [x for x in c["checks"] if x[0] == "o_own"]
    t["name"] = c["name"] + "_tail"
    t["meta"] = dict(c["meta"], fn="attend_tail")
    return t


def per_position(case, fn):
    """Apply fn to each position's op list (op-major cases de-interleaved, then re-interleaved)."""
    ops, reps, om = case["ops"], case["meta"].get("reps", 1), case["meta"].get("op_major", False)
    k = len(ops) // reps
    assert k * reps == len(ops)
    if om:
        pos = [[ops[j * reps + r] for j in range(k)] for r in range(reps)]
    else:
        pos = [ops[r * k:(r + 1) * k] for r in range(reps)]
    new = [fn(p) for p in pos]
    k2 = len(new[0])
    return [new[r][j] for j in range(k2) for r in range(reps)] if om else [o for p in new for o in p]


def cmd_prep(a):
    import rtl_hdc_v41x_vec_kr_campaign as K
    import w11_su_fuse as FU
    blob = pickle.loads(Path(a.cases).read_bytes())
    stem = Path(a.cases).stem
    out = Path(a.out)
    il_cases, kr_cases, rep = [], [], {}
    for cs in blob["cases"]:
        c = copy.deepcopy(cs)
        fn = c["meta"]["fn"]
        if fn in IL:
            c["ops"] = per_position(c, IL[fn])
            c["meta"]["lever_il"] = True
        il_cases.append(c)
        k = copy.deepcopy(c)
        ops = []
        for o in k["ops"]:
            g = K.op_defaults()
            g.update(o)
            ops.append(g)
        fops, r = FU.fuse_bench(ops, a.n, a.m, a.kr)
        k["ops"] = fops
        k["meta"]["lever_kr"] = dict(depth=a.kr, **{x: r[x] for x in ("edges", "producers", "elided", "lw", "peak")})
        kr_cases.append(k)
        rep[c["name"]] = dict(ops=len(cs["ops"]), il_ops=len(c["ops"]), kr=k["meta"]["lever_kr"])
        print(f"{c['name']:24s} ops {len(cs['ops']):3d} -> il {len(c['ops']):3d}  kr {k['meta']['lever_kr']}")
    sha = blob.get("snapshots_sha256")
    (out / f"{stem}_il.pkl").write_bytes(pickle.dumps(dict(cases=il_cases, snapshots_sha256=sha)))
    (out / f"{stem}_ilkr{a.kr}{'' if a.n == DM.SU_N else f'_N{a.n}'}.pkl").write_bytes(pickle.dumps(dict(cases=kr_cases, snapshots_sha256=sha)))
    (out / f"{stem}_prep.json").write_text(json.dumps(rep, indent=1) + "\n")
    return 0


def cmd_prep2(a):
    """il + dr (hc_post's dead reduction) + the attention tails, and the same with kr fusion."""
    import rtl_hdc_v41x_vec_campaign as VC
    import rtl_hdc_v41x_vec_kr_campaign as K
    import w11_su_fuse as FU
    blob = pickle.loads(Path(a.cases).read_bytes())          # the *_il.pkl set
    stem = Path(a.cases).stem
    out = Path(a.out)
    dr, tails = [], []
    for cs in blob["cases"]:
        c = copy.deepcopy(cs)
        if c["meta"]["fn"] == "hc_post":
            c["ops"] = per_position(c, dr_hc_post)
            c["meta"]["lever_dr"] = True
        dr.append(c)
        if c["meta"]["fn"] == "attend":
            tails.append(attend_tail_case(c, VC))
    dr += tails
    kr = []
    for c in dr:
        k = copy.deepcopy(c)
        ops = []
        for o in k["ops"]:
            g = K.op_defaults()
            g.update(o)
            ops.append(g)
        k["ops"], r = FU.fuse_bench(ops, a.n, a.m, a.kr)
        k["meta"]["lever_kr"] = dict(depth=a.kr, **{x: r[x] for x in ("edges", "producers", "elided", "lw", "peak")})
        kr.append(k)
        print(f"{c['name']:26s} ops {len(c['ops']):3d} kr {k['meta']['lever_kr']}")
    sha = blob.get("snapshots_sha256")
    if a.n == DM.SU_N:
        (out / f"{stem}dr.pkl").write_bytes(pickle.dumps(dict(cases=dr, snapshots_sha256=sha)))
    (out / f"{stem}drkr{a.kr}{'' if a.n == DM.SU_N else f'_N{a.n}'}.pkl").write_bytes(pickle.dumps(dict(cases=kr, snapshots_sha256=sha)))
    return 0


def cmd_check(a):
    """The transformed cases through the unit's bit-level reference (KR build's reference for kr cases)."""
    if a.kr:
        import rtl_hdc_v41x_vec_kr_campaign as K
        K.KR = a.kr
        sys.modules["rtl_hdc_v41x_vec_campaign"] = K
    return DM.cmd_su_check(a)


def cmd_run(a):
    """tools/dshbm_baseline_measure.cmd_su_run on the KR build of the unit when --kr > 0 (KR_DEPTH = --kr)."""
    if a.kr:
        import rtl_hdc_v41x_vec_kr_campaign as K
        K.KR = a.kr
        sys.modules["rtl_hdc_v41x_vec_campaign"] = K
    rc = DM.cmd_su_run(a)
    return rc


# ---- compose ------------------------------------------------------------------------------------------------------
def best_of(recs):
    """Per chain, the fastest EXACT measurement among the variant records (a compiler choice per chain)."""
    rows = {}
    for tag, r in recs:
        for c in r["chains"]:
            if not DM.su_exact(c):
                continue
            cur = rows.get(c["chain"])
            if cur is None or c["cycles_end"] < cur["cycles_end"]:
                rows[c["chain"]] = dict(c, variant=tag)
    base = recs[0][1]
    names = list(dict.fromkeys(c["chain"] for _, r in recs for c in r["chains"]))
    return dict(base, chains=[rows[n] for n in names if n in rows])


PV_PHASE_FAST = 609 - 248     # the tile job's p.v phase (results/rtl/v41_full_attention_numeric mixed640: pv_first
                               # 248 -> last_pv 609 fast cycles); the window-only T128 job: 225 - 120
PV_PHASE = {640: 609 - 248, 128: 225 - 120}


def attend_overlap(rec):
    """The attention chain priced as a pipeline with the tile instead of after it: max + exp (P written) precede
    the tile's p.v; the sum, sink exp and denominator run under the p.v phase; the normalisation + inverse RoPE
    follow it.  SU critical cycles = P written (the exp ops' last write, measured in the full chain) + the measured
    tail case (cycles_end - first emit).  Valid only when the denominator is written before p.v ends (checked)."""
    full = {c["chain"]: c for c in rec["chains"] if c["fn"] == "attend" and DM.su_exact(c)}
    out = {}
    for c in rec["chains"]:
        if c.get("fn") != "attend_tail" or not DM.su_exact(c):
            continue
        f = full.get(c["chain"][:-len("_tail")])
        if f is None:
            continue
        P = f.get("reps", 1)
        po = f["per_op"]
        k = len(po) // P
        idx = (lambda j: [j * P + r for r in range(P)]) if f.get("op_major") else (lambda j: [r * k + j for r in range(P)])
        e_written = max(po[i]["last_write"] for i in idx(1))
        den_written = max(po[i]["last_write"] for i in idx(3))
        tail = c["cycles_end"] - min(p["first_emit"] for p in c["per_op"] if p["first_emit"] is not None)
        T = f["T"]
        pv_su = PV_PHASE[T] * DM.F_SER / DM.F_FAST
        ok = den_written <= e_written + pv_su
        key = f"attend.T{T}"
        crit = e_written + tail
        if ok and (key not in out or crit > out[key]["cycles"]):
            out[key] = dict(cycles=crit, p_written=e_written, den_written=den_written, tail=tail,
                            pv_phase_su_cycles=round(pv_su, 1), full_chain=f["cycles_end"])
    return out


_SU_TABLE = DM.su_table


def su_table_overlap(rec, rec2=None, P=1):
    t = _SU_TABLE(rec, rec2, P)
    if rec2 is None and P == 1:
        for k, v in attend_overlap(rec).items():
            if k in t:
                t[k] = min(t[k], v["cycles"])
    return t


ILV_T640_6POS = 2560    # results/rtl/dshbm_verify_tile_batch_20261004 (branch claude/dshbm-verify-tile-batch-20261004):
                        # the W11 engine's position-interleaved verify mode, 6 positions at T 640, SU latency 218 in
                        # the loop (conservative row; the SU chain is still charged in full on top)
_PRICE_LOCAL = DM.price_local


def price_local_ilv(op, su, f_ser, flags, WC, m, P=1):
    us, how = _PRICE_LOCAL(op, su, f_ser, flags, WC, m, P)
    if op["fn"] == "attend" and op.get("yarn") and P == 6:
        us -= (6 * DM.ATT_TILE[640] - ILV_T640_6POS) / DM.F_FAST * 1e6
        how += " + ILV tile (6 positions, measured)"
    return us, how


def compose(base_dir, su1, su6, overlap=False, ilv=False):
    DM.su_table = su_table_overlap if overlap else _SU_TABLE
    DM.price_local = price_local_ilv if ilv else _PRICE_LOCAL
    import w19_hbm_token_compose as WC
    out = Path(base_dir)
    prog = json.loads((out / "program.json").read_text())
    sm = WC.SMTable([json.loads((ROOT / "results/rtl/w19_sm_real_ops.json").read_text()),
                     json.loads((out / "sm_real_ops.json").read_text())], "ar")
    coll = WC.w15_prod(json.loads((ROOT / "results/rtl/w15_hbm_nvls.json").read_text()), "hbm_p48_ss")
    coll["select_cycles"] = 419
    base = dict(prog=prog, sm=sm, coll=coll, su=DM.su_table(su1), WC=WC)
    r = DM.mtp_and_accelerator(prog, base, su1, su6)
    sw = ("tomahawk_ultra_protocol", "board")
    ar = DM.compose_program(**base, f_sm=DM.F_FAST, switch=sw)
    DM.su_table = _SU_TABLE
    DM.price_local = _PRICE_LOCAL
    return dict(ilv_tile=ilv, attend_overlap=dict(p1=attend_overlap(su1), p6=attend_overlap(su6)) if overlap else None,
                ar_us=r["measured"]["ar_us"], ar_tok_s=r["measured"]["ar_tok_s"], ar_parts_us=r["measured"]["ar_parts_us"],
                mtp=r["measured"]["mtp"], mtp_tok_s=r["measured"]["mtp_tok_s"],
                sensitivity_one_tile_job=r["measured"]["sensitivity_tile_one_job_for_6_positions"],
                local_by_fn_us_ar=ar["local_by_fn_us"], su_chain_cycles_p1=DM.su_table(su1),
                unvalidated_terms=r["unvalidated_terms"])


def cmd_compose(a):
    variants = []
    for v in a.variants:
        name, files = v.rsplit("=", 1)
        ov = "+ov" in name
        ilv = "+ilv" in name
        f1, f6 = files.split(",")
        variants.append((name, json.loads(Path(f1).read_text()), json.loads(Path(f6).read_text()), ov, ilv))
    res, prev = {}, None
    acc1, acc6 = [], []
    for name, r1, r6, ov, ilv in variants:                   # cumulative: each lever on top of the previous ones
        if name.startswith("="):                             # a new hardware configuration: its own records only
            name, acc1, acc6 = name[1:], [], []
        acc1.append((name, r1))
        acc6.append((name, r6))
        c = compose(a.base, best_of(acc1), best_of(acc6), overlap=ov, ilv=ilv)
        if prev is not None:
            c["gain_vs_previous"] = dict(
                ar_pct=round(100 * (c["ar_tok_s"] / prev["ar_tok_s"] - 1), 2),
                mtp_pct=round(100 * (c["mtp_tok_s"] / prev["mtp_tok_s"] - 1), 2),
                ar_us=round(prev["ar_us"] - c["ar_us"], 2),
                verify_us=round(prev["mtp"]["verify_p6_us"] - c["mtp"]["verify_p6_us"], 2))
        res[name] = c
        prev = c
        print(f"{name:12s} AR {c['ar_tok_s']:8.1f} tok/s ({c['ar_us']:.2f} us)  MTP {c['mtp_tok_s']:8.1f} "
              f"(verify {c['mtp']['verify_p6_us']:.2f} us) local AR {c['ar_parts_us']['local']:.2f} "
              f"{c.get('gain_vs_previous', '')}")
    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(dict(variants=res), indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("prep", "prep2", "check", "run", "compose"))
    ap.add_argument("--out", default=".")
    ap.add_argument("--cases", default="su_cases.pkl")
    ap.add_argument("--kr", type=int, default=0)
    ap.add_argument("--work", default=None)
    ap.add_argument("--bcast", type=int, default=4)
    ap.add_argument("--ret", type=int, default=5)
    ap.add_argument("--mlat", type=int, default=4)
    ap.add_argument("--alat", type=int, default=3)
    ap.add_argument("--n", type=int, default=DM.SU_N)
    ap.add_argument("--m", type=int, default=DM.SU_M)
    ap.add_argument("--fp", choices=("rtl", "dpi", "dpi_beh"), default="dpi_beh")
    ap.add_argument("--base", default="results/rtl/dshbm_baseline_measured_20261004")
    ap.add_argument("--variants", nargs="*", default=[])
    ap.add_argument("--record", default=None)
    a = ap.parse_args()
    if a.step in ("prep", "prep2") and not a.kr:
        a.kr = KR_DEFAULT
    raise SystemExit(dict(prep=cmd_prep, prep2=cmd_prep2, check=cmd_check, run=cmd_run, compose=cmd_compose)[a.step](a))
