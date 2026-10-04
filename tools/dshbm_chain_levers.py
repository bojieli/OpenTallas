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
        fops, r = FU.fuse_bench(ops, DM.SU_N, DM.SU_M, a.kr)
        k["ops"] = fops
        k["meta"]["lever_kr"] = dict(depth=a.kr, **{x: r[x] for x in ("edges", "producers", "elided", "lw", "peak")})
        kr_cases.append(k)
        rep[c["name"]] = dict(ops=len(cs["ops"]), il_ops=len(c["ops"]), kr=k["meta"]["lever_kr"])
        print(f"{c['name']:24s} ops {len(cs['ops']):3d} -> il {len(c['ops']):3d}  kr {k['meta']['lever_kr']}")
    sha = blob.get("snapshots_sha256")
    (out / f"{stem}_il.pkl").write_bytes(pickle.dumps(dict(cases=il_cases, snapshots_sha256=sha)))
    (out / f"{stem}_ilkr{a.kr}.pkl").write_bytes(pickle.dumps(dict(cases=kr_cases, snapshots_sha256=sha)))
    (out / f"{stem}_prep.json").write_text(json.dumps(rep, indent=1) + "\n")
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
    return dict(base, chains=[rows[c["chain"]] for c in base["chains"] if c["chain"] in rows])


def compose(base_dir, su1, su6):
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
    return dict(ar_us=r["measured"]["ar_us"], ar_tok_s=r["measured"]["ar_tok_s"], ar_parts_us=r["measured"]["ar_parts_us"],
                mtp=r["measured"]["mtp"], mtp_tok_s=r["measured"]["mtp_tok_s"],
                sensitivity_one_tile_job=r["measured"]["sensitivity_tile_one_job_for_6_positions"],
                local_by_fn_us_ar=ar["local_by_fn_us"], su_chain_cycles_p1=DM.su_table(su1),
                unvalidated_terms=r["unvalidated_terms"])


def cmd_compose(a):
    variants = []
    for v in a.variants:
        name, files = v.split("=")
        f1, f6 = files.split(",")
        variants.append((name, json.loads(Path(f1).read_text()), json.loads(Path(f6).read_text())))
    res, prev = {}, None
    acc1, acc6 = [], []
    for name, r1, r6 in variants:                   # cumulative: each lever on top of the previous ones
        acc1.append((name, r1))
        acc6.append((name, r6))
        c = compose(a.base, best_of(acc1), best_of(acc6))
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
    ap.add_argument("step", choices=("prep", "check", "run", "compose"))
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
    if a.step == "prep" and not a.kr:
        a.kr = KR_DEFAULT
    raise SystemExit(dict(prep=cmd_prep, check=cmd_check, run=cmd_run, compose=cmd_compose)[a.step](a))
