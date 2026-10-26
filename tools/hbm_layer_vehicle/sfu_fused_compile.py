#!/usr/bin/env python3
"""VEH-FMT-SFU (10-19): static compiler FUSED.* -> col_sfu_SW arithmetic-grid programme (compiler_control rows) for the
d4g SW slice, plus the per-record feasibility audit of HC_PRE_NORM / HC_POST / QDQ_FP8 on that unit.

STATUS 10-19 (VEH-FMT-SFU): DRAFT, NOT RTL-qualified.  The arithmetic schedule below addresses VM words directly and
feeds the next pass from the previous pass's output; the real engine (ot_hgi_sfu_static_engine: per-stream input SRAM
groups filled by stage_*, scalar registers for broadcasts, a separate output group read only by drain_*) needs
operand-store-local addresses, scalar loads for B / D and a drain -> VM -> stage round trip between passes
(results/rtl/hbm_ds_layer_tput_1018/slice_sw/sfu/fused/manifest.json rtl_precheck).

Unit of record (GEN2 die.v / sw2 slice.v): sfucore_SW = ot_hgi_sfu_core_split3 -> ot_hgi_sfu_arithmetic_grid: sixteen
ot_su12_sfu lanes (KIND 1, GSH 1, KIMM 1, DENR 1, DRING 3), one element a lane a cycle, ONE control row a cycle
(1742 b, tools/hbm_static/sfu_control_image.FIELDS) from sfup_SW (ot_hgi_sfu_programme_store_r10 PAGE_AW 1: 2,048 rows,
start_loops replays the SAME rows -> no address advance, so a programme's rows >= its beats).

HC_POST (exact golden hdc_golden_v41.Model.hc_post, ds_native unit: post = C[0:4], comb[j, k] = C[4 + 4 j + k]):
    out_k = to_bf16(add(mul(post_k, y), seqsum_j mul(comb_jk, res_j)))       j = 0..3 in order
  lowered on the quadrant's hidden slice (d4g C2: HC_POST is element-wise on the quadrant slice, SW = elements
  [0, D/4)) to FOUR passes of ONE fixed lane configuration (M1_AB: A x B, Q: C x D, AD_Q: (A x B) + (C x D)):
    P1  O_k <- r0 x c0k + r1 x c1k                (golden add(mul(c0k, r0), mul(c1k, r1)); FP mul / add commute)
    P2  O_k <- r2 x c2k + O_k x 1.0               (golden add(t1, mul(c2k, r2)); t x 1.0 = t, RTL-checked)
    P3  O_k <- r3 x c3k + O_k x 1.0
    P4  O_k <- y  x post_k + O_k x 1.0, co_rnd    (golden to_bf16(add(mul(post_k, y), mix_k)))
  B and D are scalar broadcasts (stride 0) of VM words: the coefficients are RUN-TIME VM data (HC_MIX output), no
  immediate, no IO scalar path; D of P2..P4 is ONE VM word holding 1.0 (layout requirement: `one` below).
  Passes are k-interleaved (P1 k0..k3, P2 k0..k3, ...): a pass reads O_k that the previous pass wrote 3 x beats_k
  rows earlier (>= the drain horizon, asserted).  The only field that changes between passes is co_rnd (OUT stage):
  a gap of GAP rows without emits before P4 lets every P3 element leave OUT before co_rnd turns on (GAP > drain).
  O is computed in place (h is not read by HC_POST: B reads RES).

HC_PRE_NORM and QDQ_FP8 are NOT lowerable on col_sfu_SW (audit(), evidence in the manifest): rsqrt is the scalar side
pipe of a KIND-2 lane only (ot_su12_full: SU qcore lane 0); the grid's KIND-1 lanes have side_y tied 0; reductions
(RMSNorm sum of squares, per-32 amax) leave a lane only through ro_v / ro_x, and sfucore_SW__ro_* are unconnected in
slice.v (no reducer); the d4g die has a QDQ engine (hb_quant_NW, ot_hgi_qdq_host_split) in NW, outside the SW slice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / "hbm_static"))

from sfu_control_image import WIDTH as CTL_W, pack  # noqa: E402

ROWS = 2048                  # sfup_SW rows (PAGE_AW 1)
LANES = 16
LEAD = 8                     # offset-bank load lead (sfu_vector_calendar)
import leaf_split_latency as LS  # noqa: E402  HBM-P6-CMP over-cap leaf-split shifts (opt-in OT_HBM_LEAF_SPLIT)
# drain horizon of a non-dividing, SFU-free op (sfu_vector_calendar); + LS 'sfu_op_horizon' (3) on the split core _sp2
HORIZON = 46 + LS.shift('sfu_op_horizon')
GAP = 64                     # rows without emits before the co_rnd pass (> HORIZON)
TAIL = 16                    # rows after the drain horizon: the last beats' OUT-stage co_rnd (RTL: 46 rows short by 3)
VB_LAG = 0                   # rows the vector bases trail the emit row (lane_map: pass ring vs emit pipe; RTL-measured)
ONE = 0x3F800000
M1_AB, QM_POS, AD_Q, DST_VM = 1, 1, 1, 1      # lane localparams (ot_hdc_v41x_vec_lane_c12.sv)


def okey(v):
    return (~v & 0xFFFFFFFF) if v >> 31 else v | 0x80000000


def hc_post_passes(*, D, quadrant, A, B, C, O, one, order=(0, 1, 2, 3), comb_t=False):
    """the 4 x 4 (pass, k) segments: dict(a, b, c, d, o bases, rnd).  order / comb_t: mutant knobs (golden: identity)."""
    n = D // 4
    lo = quadrant * n
    j0, j1, j2, j3 = order

    def cf(j, k):
        return C + 4 + (4 * k + j if comb_t else 4 * j + k)
    segs = []
    for p in range(4):
        for k in range(4):
            o = O + k * D + lo
            if p == 0:
                s = dict(a=B + j0 * D + lo, b=cf(j0, k), c=B + j1 * D + lo, d=cf(j1, k))
            elif p in (1, 2):
                j = (j2, j3)[p - 1]
                s = dict(a=B + j * D + lo, b=cf(j, k), c=o, d=one)
            else:
                s = dict(a=A + lo, b=C + k, c=o, d=one)
            segs.append(dict(s, o=o, p=p, k=k, n=n, rnd=int(p == 3)))
    return segs


def compile_segments(segs, gap=GAP, check=True, vb_lag=None):
    """fixed control rows of a k-interleaved multi-pass programme with one lane configuration (M1_AB + Q, AD_Q)."""
    n = segs[0]["n"]
    assert all(s["n"] == n for s in segs)
    beats = -(-n // LANES)
    strides = (1, 0, 1, 0, 1)                    # A contiguous, B broadcast, C contiguous, D broadcast, O contiguous
    terms = sum((strides[s] << b) << (24 * (s * 10 + b)) for s in range(5) for b in range(4))
    base = dict(ld_bank=0, bank=0, no=1, ni=n, ls=4, lvw=4, ld_c=terms, dst=DST_VM, cx_imm3=okey(ONE),
                cp_m1=M1_AB, cm_m1=M1_AB, cm_qm=QM_POS, ca_ad=AD_Q, cp_imm1=ONE, cm_imm1=ONE, ca_imm2=ONE,
                cs_imm2=ONE, ce_imm1=ONE, co_dst=DST_VM)
    emits = []                                   # (row, seg index, beat)
    row = LEAD
    rnd_from = None
    for si, s in enumerate(segs):
        if s["rnd"] and rnd_from is None:
            row += gap
            rnd_from = row
        for b in range(beats):
            emits.append((row, si, b))
            row += 1
    last = row - 1
    cycles = last + 1 + HORIZON + TAIL
    if check and cycles > ROWS:
        raise ValueError(f"programme {cycles} rows > sfup_SW {ROWS}: not resident-installable")
    # RAW distance: a pass reads O_k that the previous pass wrote; first read row - last write emit row > HORIZON
    first = {}
    lastw = {}
    for r, si, b in emits:
        first.setdefault(si, r)
        lastw[si] = r
    for si, s in enumerate(segs):
        for sj in range(si):
            t = segs[sj]
            if check and t["o"] in (s["c"], s["a"]) and not first[si] - lastw[sj] > HORIZON:
                raise ValueError(f"RAW hazard seg {sj} -> {si}: {first[si] - lastw[sj]} rows")
    if check and rnd_from is not None:
        prev = max(r for r, si, b in emits if not segs[si]["rnd"])
        assert rnd_from - prev > HORIZON
    lag = VB_LAG if vb_lag is None else vb_lag
    em = {r: (si, b) for r, si, b in emits}
    vbr = {r + lag: (si, b) for r, si, b in emits}
    words = []
    for c in range(cycles):
        f = dict(base, ld=int(c == 0), co_rnd=int(rnd_from is not None and c >= rnd_from))
        if c in em:
            si, b = em[c]
            f.update(emit=1, i_v=LANES * b)
        if c in vbr:
            si, b = vbr[c]
            s = segs[si]
            f.update(vb=sum((s[k] + LANES * b * strides[i]) << (24 * i) for i, k in enumerate("abcdo")))
        words.append(pack(f))
    return dict(words=words, cycles=cycles, beats_per_seg=beats, emit_rows=len(emits), rnd_from=rnd_from,
                first_emit=LEAD, last_emit=last)


def golden_hc_post_slice(y, res, pc, quadrant):
    """numpy mirror of hdc_golden_v41 hc_post on one quadrant slice (FP32 RNE ops, BF16 RNE store), as uint32."""
    import hdc_golden_v41 as GV                  # noqa: E402  (tools/ on sys.path)
    D = len(y)
    n = D // 4
    sl = slice(quadrant * n, (quadrant + 1) * n)
    yf = y.view(np.float32)[sl]
    rf = res.view(np.float32).reshape(4, D)[:, sl]
    c = pc.view(np.float32)
    post, comb = c[:4], c[4:20].reshape(4, 4)
    mix = [GV.seqsum([GV.mul(comb[j, k], rf[j]) for j in range(4)]) for k in range(4)]
    out = GV.to_bf16(np.stack([GV.add(GV.mul(post[k], yf), mix[k]) for k in range(4)]))
    return np.asarray(out, dtype=np.float32).view(np.uint32)


def audit():
    return {
        "FUSED.HC_POST": dict(status="lowered", unit="col_sfu_SW grid (16 KIND-1 lanes)",
                              note="4 passes / quadrant slice, coefficients VM broadcast, 1.0 VM word"),
        "FUSED.HC_PRE_NORM": dict(status="not_lowerable_on_col_sfu", reasons=[
            "RMSNorm rsqrt: SFU_RSQRT is the scalar side pipe of a KIND-2 lane (ot_su12_full, SU qcore lane 0); "
            "ot_hgi_sfu_arithmetic_grid's 16 lanes are ot_su12_sfu (KIND 1) with side_y tied 0",
            "sum of squares (split_sum) is a cross-element reduction: a lane exports it only on ro_v / ro_x and "
            "sfucore_SW__ro_{v,x}_{w,n,e,s} are unconnected in slice.v (no reducer on the SFU core)",
            "the priced engine (ot_hgi_fused_record HCE/HLL, ds_native FUSED_HLL, 649 cyc) is NOT in the d4g "
            "GEN2 die.v module inventory"],
            candidate="SU qcore (su_SW: KIND-2 lane 0 side-pipe rsqrt + stree scalar reduction, as the q_norm SU "
                      "template) for the RMSNorm; hc_pre mix seqsum is element-wise and fits the col_sfu grid "
                      "(1 pass: pre_j broadcast, 2 products a pass) -> COORD decision"),
        "FUSED.QDQ_FP8": dict(status="not_lowerable_on_col_sfu", reasons=[
            "per-32 block amax is a reduction (ro_x unconnected); UE8M0 exponent extraction / FP8 grid rounding are "
            "not grid ops",
            "the d4g die has the QDQ engine hb_quant_NW (ot_hgi_qdq_host_split RL 7 WC 4 COMPACT 1) in quadrant NW "
            "(outside the SW cut) -> its payload belongs to the NW cut (VEH-CUTS)"]),
    }


def hexrows(words, width):
    return "".join(f"{w:0{-(-width // 4)}x}\n" for w in words)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", nargs="+", type=Path, required=True)
    ap.add_argument("--quadrant", type=int, default=0)
    ap.add_argument("--one", type=int, default=(1 << 17) - 1, help="VM word holding 1.0 (layout requirement)")
    ap.add_argument("--pre", type=Path, help="write tb_sfu_grid inputs here")
    ap.add_argument("--manifest", type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(TOOLS))
    cases, recs = [], []
    for fd in a.fixtures:
        z = np.load(fd / "operands.npz")
        r = json.loads((fd / "records.json").read_text())
        for _, rr in sorted(r["records"].items()):
            for x in rr:
                if x["op"] != "FUSED.HC_POST":
                    continue
                d = x["desc"]
                key = f"r0.k{x['k']}"
                y, res, pc, O = (z[f"{key}.{n}"] for n in ("A", "B", "C", "O"))
                D = d["A"][1]
                gold = golden_hc_post_slice(y, res, pc, a.quadrant)
                n = D // 4
                fx = O.reshape(4, D)[:, a.quadrant * n:(a.quadrant + 1) * n]
                assert np.array_equal(gold, fx), f"golden mirror != fixture O ({fd.name} k{x['k']})"
                name = f"ds_l{x['layer']}_k{x['k']}_q{a.quadrant}"
                segs = hc_post_passes(D=D, quadrant=a.quadrant, A=d["A"][0], B=d["B"][0], C=d["C"][0],
                                      O=d["O"][0], one=a.one)
                prog = compile_segments(segs)
                recs.append(dict(name=name, layer=x["layer"], k=x["k"], tag=x["tag"], D=D, slice_n=n,
                                 rows=prog["cycles"], emit_rows=prog["emit_rows"], rnd_from=prog["rnd_from"],
                                 priced=[p["base_cost"] for p in x["priced"]],
                                 ctl_sha256=hashlib.sha256(hexrows(prog["words"], CTL_W).encode()).hexdigest()))
                cases.append((name, prog, d, a.one, z, key, gold, n))
                if len(cases) == 1:              # mutant witnesses on the first record (each must FAIL on the RTL)
                    for vn, kw in (("mut_order", dict(order=(0, 2, 1, 3))), ("mut_comb_t", dict(comb_t=True))):
                        ms = hc_post_passes(D=D, quadrant=a.quadrant, A=d["A"][0], B=d["B"][0], C=d["C"][0],
                                            O=d["O"][0], one=a.one, **kw)
                        cases.append((f"{name}_{vn}", compile_segments(ms), d, a.one, z, key, gold, n))
                    cases.append((f"{name}_mut_gap", compile_segments(segs, gap=0, check=False), d, a.one, z, key,
                                  gold, n))
    if a.pre:
        a.pre.mkdir(parents=True, exist_ok=True)
        lst = []
        for name, prog, d, one, z, key, gold, n in cases:
            (a.pre / f"{name}.ctl.hex").write_text(hexrows(prog["words"] + [0] * (ROWS - len(prog["words"])), CTL_W))
            vm = {}
            D = d["A"][1]
            for s in ("A", "B", "C"):
                for i, w in enumerate(z[f"{key}.{s}"]):
                    vm[d[s][0] + i] = int(w)
            vm[one] = ONE
            (a.pre / f"{name}.vm.txt").write_text("".join(f"{ad:x} {w:08x}\n" for ad, w in sorted(vm.items())))
            exp = {}
            for k in range(4):
                for i in range(n):
                    exp[d["O"][0] + k * D + a.quadrant * n + i] = int(gold[k, i])
            (a.pre / f"{name}.exp.txt").write_text("".join(f"{ad:x} {w:08x}\n" for ad, w in sorted(exp.items())))
            lst.append(f"{name} {prog['cycles']} {len(vm)} {len(exp)}")
        (a.pre / "cases.txt").write_text("\n".join(lst) + "\n")
    man = dict(schema="opentallas.hbm_sfu_fused_compile.v1", unit="col_sfu_SW / sfucore_SW grid", quadrant=a.quadrant,
               layout_requirements=dict(one_word=a.one, note="one VM word = 1.0 FP32 (D operand of P2..P4)"),
               price_assumptions=dict(
                   resident="programmes installed ONCE per run (one install ~0.79 M ingress edges, sfu_images.py); "
                            "per token only prm row + descriptor + launch",
                   shared_programme="the attn and ffn HC_POST of every layer share ONE resident programme only if the "
                                    "compiler gives them the same VM bases (y/yf, MIXa/MIXf differ in ds_native: "
                                    "2 programmes x rows below > 2,048 -> a layout change is owed)"),
               records=recs, audit=audit())
    if a.manifest:
        a.manifest.parent.mkdir(parents=True, exist_ok=True)
        a.manifest.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(dict(records=len(recs), rows=sorted({r["rows"] for r in recs}), cases=len(cases))))


if __name__ == "__main__":
    main()
