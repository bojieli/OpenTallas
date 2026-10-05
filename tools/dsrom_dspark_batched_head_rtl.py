#!/usr/bin/env python3
"""DS-ROM DSpark draft lever L2: the BATCHED head, measured on the minimum component (one head phase of the
V4.1 ROM-array element, rtl/v41rom/ot_v41_rom_elem_nv_w10.sv NV = 5, on a small element array with its return
network), bit-exact against the golden.

Golden dependency (tools/hdc_golden_v41.py Model.draft):
    logits = [mv(head.weight, rmsnorm_bf16(x_i, norm)) for x_i in xh]        # all 5 rows, no draft token read
    for i: logits[i] = add(logits[i], mv(markov_head.head, markov_head.embed[out[i]])); out.append(argmax(logits[i]))
so logits_i = head(h_i) (one FP32 node per row: the chunk8 csum of the exact BF16 products) + markov(d_i) (its own mv),
joined by ONE FP32 add (RNE), then a first-max argmax.  There is no separate vocabulary bias: the Markov matvec IS
the per-token bias.  head(h_i) depends only on h_i, so the 5 head matvecs may share one ROM sweep; only the Markov
matvec, the add and the argmax stay serial.  The tool asserts the source still reads that way.

Configurations (same checkpoint rows, same 5 x vectors, the same W10 gate machinery
tools/w10_validation/rtl_v41_rom_array.py, FAST PP BP=2 NB=2, the element swapped by binding):
  serial   NV = 1 (the w10 element), 5 positions position-outer: five ROM sweeps (as built)
  batched  NV = 5, 5 positions round-outer / position-inner: ONE ROM sweep
  single   NV = 1, 1 position (the one-sweep reference)
Every row of every position must equal the golden FP32 head logit (G.mv under chunk8) and its BF16 bit for bit.

    python3 tools/dsrom_dspark_batched_head_rtl.py --work DIR [--n 16 32] [--output results/rtl/.../record.json]
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from w10_validation import rtl_v41_rom_array as gate  # noqa: E402

G, S = gate.G, gate.S
SNAP = Path("/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/"
            "dba1be0a40aa45a94ad051997016db3960a90277")
ARRAY = "rtl/test/w10_validation/ot_v41_rom_array_w10_test.sv"
ELEM = "rtl/v41rom/ot_v41_rom_elem_w10.sv"
ELEM_NV = "rtl/v41rom/ot_v41_rom_elem_nv_w10.sv"
GAMMA = 5
HEAD_R0 = 1000          # vocabulary rows of the bench (lm_head rows r0 .. r0 + R)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_golden_dependency():
    """The draft's head rows are computed before the Markov loop and the loop only adds and selects."""
    src = next(inspect.getsource(c.draft) for c in vars(G).values() if inspect.isclass(c) and hasattr(c, "draft")
               and c.__module__ == G.__name__)
    need = ['logits = [mv(self.w["head.weight"], rmsnorm_bf16(x, self.lw(Lf, "norm.weight"), self.eps)) for x in xh]',
            "logits[i] = add(logits[i], mv(mhead, e))",
            "out.append(int(np.argmax(logits[i])))"]
    lines = [ln.strip() for ln in src.splitlines()]
    pos = [next(i for i, ln in enumerate(lines) if n in ln) for n in need]
    assert pos == sorted(pos), pos
    loop = next(i for i, ln in enumerate(lines) if ln.startswith("for i in range(B):"))
    assert pos[0] < loop < pos[1], "the head rows must be formed before the Markov loop"
    return dict(additive=True, head_rows_before_loop=True, rounding_points=[
        "head(h_i) = mv(head.weight, bf16 x_i): exact BF16 products, chunk8 csum (chunks of 8 sequential from +0, "
        "pairwise tree), one FP32 node per row",
        "markov(d_i) = mv(markov_head.head, markov_head.embed[d_i]) (FP32, its own chunk8 csum)",
        "logits_i = add(head, markov): one FP32 RNE add",
        "d_{i+1} = argmax(logits_i) (first maximum)"], bias="none beyond the Markov matvec",
        golden_lines=need)


# ---------------------------------------------------------------------------------------------------------
# the batched x stream: build_phase with the round loop turned round-outer, position-inner
# ---------------------------------------------------------------------------------------------------------
_src = inspect.getsource(gate.build_phase)
_OLD = """    for (pos, (q, b)) in [(pos, qb) for pos in range(npos) for qb in sorted(rounds)]:
        xc, xe, xbits = xcs[pos], xes[pos], xbs[pos]
        ptag = (pos << 1613) | (pos << 1610)
        units = sorted(rounds[(q, b)])
        dmax = max(v for (qq, bb, _), v in demand.items() if (qq, bb) == (q, b))
        rl = max(S.FADD_REC, len(units), dmax)
        if bf:"""
_NEW = """    for (pos, (q, b)) in ([(-1, qb) for qb in sorted(rounds)] if BATCHED else
                          [(pos, qb) for pos in range(npos) for qb in sorted(rounds)]):
        units = sorted(rounds[(q, b)])
        dmax = max(v for (qq, bb, _), v in demand.items() if (qq, bb) == (q, b))
        if pos < 0:
            assert bf, "batching is a BF16 (head) mechanism"
            groups = [units[i:i + XS] for i in range(0, len(units), XS)]
            seq = [(p, g) for g in groups for p in range(npos)]
            rl = max(S.FADD_REC, len(seq) + 1, S.BF16_WORD_CYCLES * dmax)
            slots = [None] * rl
            span = rl - 1
            for i, pg in enumerate(seq):
                slots[(i * span) // len(seq)] = pg
            for pg in slots:
                if pg is None:
                    beats.append(0)
                    continue
                p, g = pg
                v = (1 << (265 * XS + 3)) | (b << (265 * XS))
                for k, u in enumerate(g):
                    d = 0
                    for lane in range(16):
                        d |= int(xbs[p][u * 128 + lane * 8 + b]) << (16 * lane)
                    v |= (1 << (264 * XS + k)) | (u << (256 * XS + 8 * k)) | (d << (256 * k))
                bw = 265 * XS + 4
                beats.append((p << (bw + 549)) | (p << (bw + 546)) | v)
            t_rounds += rl
            continue
        xc, xe, xbits = xcs[pos], xes[pos], xbs[pos]
        ptag = (pos << 1613) | (pos << 1610)
        rl = max(S.FADD_REC, len(units), dmax)
        if bf:"""
assert _src.count(_OLD) == 1, "gate build_phase changed: re-derive the batched stream patch"
_ns = dict(vars(gate))
_ns["BATCHED"] = False
_ns["XS"] = 4
exec(compile(_src.replace(_OLD, _NEW), "<batched build_phase>", "exec"), _ns)
build_phase_b = _ns["build_phase"]


RTL0 = list(gate.RTL)
TB0 = gate.TB


def _sub(src: str, pairs) -> str:
    for a, b in pairs:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    return src


def bind(work: Path, nv: int, xs: int = 4) -> list[str]:
    """The gate's source list; nv > 0: the array bound to ot_v41_rom_elem_nv_w10 #(NV, XS) (nv 0: the w10
    element).  xs = 8: the bench's BF16 beat widened to 8 slices (array and testbench bindings)."""
    gate.TB = TB0
    if nv == 0:
        return list(RTL0)
    src = _sub((ROOT / ARRAY).read_text(), [("ot_v41_rom_elem_w10 #(", f"ot_v41_rom_elem_nv_w10 #(.NV({nv}), .XS({xs}), ")])
    if xs != 4:
        src = _sub(src, [("    input  wire [3:0]   xb_sv,", f"    input  wire [{xs - 1}:0]   xb_sv,"),
                         ("    input  wire [31:0]  xb_u,", f"    input  wire [{8 * xs - 1}:0]  xb_u,"),
                         ("    input  wire [1023:0] xb_d,", f"    input  wire [{256 * xs - 1}:0] xb_d,"),
                         ("BBW = 3 + 4 + 32 + 1024;", f"BBW = 3 + {xs} + {8 * xs} + {256 * xs};"),
                         (".xb_sv(bb[BBW-4 -: 4]),", f".xb_sv(bb[BBW-4 -: {xs}]),"),
                         (".xb_u(bb[1055:1024]), .xb_d(bb[1023:0]),",
                          f".xb_u(bb[{264 * xs - 1}:{256 * xs}]), .xb_d(bb[{256 * xs - 1}:0]),")])
        bw = 265 * xs + 4
        tb = _sub((ROOT / TB0).read_text(), [
            ("reg [1063:0] bbeat = '0;", f"reg [{bw - 1}:0] bbeat = '0;"),
            (".xb_v(bbeat[1063]), .xb_b(bbeat[1062:1060]), .xb_sv(bbeat[1059:1056]),",
             f".xb_v(bbeat[{bw - 1}]), .xb_b(bbeat[{bw - 2}:{bw - 4}]), .xb_sv(bbeat[{bw - 5}:{264 * xs}]),"),
            (".xb_u(bbeat[1055:1024]), .xb_d(bbeat[1023:0]),", f".xb_u(bbeat[{264 * xs - 1}:{256 * xs}]), .xb_d(bbeat[{256 * xs - 1}:0]),"),
            ("reg [6+XBW+1064-1:0] stream", f"reg [6+XBW+{bw}-1:0] stream")])
        tbp = work / f"tb_xs{xs}_binding.sv"
        tbp.write_text(tb)
        gate.TB = str(tbp)
    out = work / f"array_nv{nv}_xs{xs}_binding.sv"
    out.write_text(src)
    return [str(out) if p == ARRAY else ELEM_NV if p == ELEM else p for p in RTL0]


def build(work: Path, N: int, nv: int, xs: int = 4) -> Path:
    gate.RTL = bind(work, nv, xs)
    obj = work / f"nv{nv}_xs{xs}"
    obj.mkdir(parents=True, exist_ok=True)
    return gate.build_sim(N, obj, gate.XF_BF, 2, mtp=1, fast=1, pp=1, bp=2)


def run(exe: Path, wd: Path, ph: dict):
    rows, done = gate.run_case(exe, wd, ph)
    rows = {t: v for t, v in rows.items() if not t[1] & gate.SENT}
    ok32 = sum(rows.get(t, (None,))[0] == v for t, v in ph["exp_fp32"].items())
    ok16 = sum(rows.get(t, (None, None))[1] == v for t, v in ph["exp_bf16"].items())
    last = max((v[3] for v in rows.values()), default=None)
    return dict(rows=len(ph["exp_fp32"]), rows_out=len(rows), fp32_exact=ok32, bf16_exact=ok16,
                fault=done[1] if done else None, cycles_last_row=last, t_rounds_scheduled=ph["t_rounds"],
                exact=ok32 == ok16 == len(ph["exp_fp32"]) == len(rows) and not (done and done[1])), rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--n", type=int, nargs="+", default=[16, 32])
    ap.add_argument("--output", type=Path)
    a = ap.parse_args(argv)
    if a.output and a.output.exists():
        raise SystemExit("refuse to overwrite a verdict")
    dep = check_golden_dependency()
    S.BF16_PAIR, S.BF16_WORD_CYCLES, S.BF16_SPLIT_BOOST = True, 8, 1
    S.IL_BF16, S.BF16_CAP, S.BF16_MAX_UNITS = 1, 3, 4
    S.FADD_REC = gate.FAST_LAT
    G.set_arith("chunk8")
    ck = gate.Ckpt(SNAP)
    cases = []
    for N in a.n:
        R = (N // 16) * 2                       # the gate's BF16 row budget on N macros (BF16_CAP, NB 2)
        mat = gate.Mat(ck, "head", "bf16", R, 4096, r0=HEAD_R0, phase="wo_a")   # the dense BF16 placement phase
        # the bench's head logits ARE the draft's: G.mv under chunk8 equals the element gate's csum reference
        xs_chk = G.to_bf16((np.random.default_rng(1).standard_normal(4096) * 0.5).astype(G.F))
        assert np.array_equal(G.bits(G.mv(mat.wf, xs_chk)), G.bits(G.csum(G.mul(mat.wf, xs_chk[None, :]))))
        res = {}
        for cfg, nv, npos, batched, xs in (("single", 0, 1, False, 4), ("serial", 0, GAMMA, False, 4),
                                           ("serial_nv1", 1, GAMMA, False, 4), ("batched", GAMMA, GAMMA, True, 4),
                                           ("batched_x2", GAMMA, GAMMA, True, 8)):
            wd = a.work / f"n{N}_{cfg}"
            wd.mkdir(parents=True, exist_ok=True)
            _ns["BATCHED"], _ns["XS"] = batched, xs
            ph = build_phase_b([mat], N, wd, np.random.default_rng(gate.SEED), nb=2, npos=npos, pp=True)
            exe = build(a.work / f"n{N}", N, nv, xs)
            r, rows = run(exe, wd, ph)
            r.update(NV=nv, XS=xs, positions=npos, batched=batched, t_phase_pred=ph["t_pred"],
                     segments_per_element=ph["elements"], split={k: v["segment_elems"] for k, v in ph["split"].items()})
            res[cfg] = r
            res[cfg]["_rows"] = rows
            print(json.dumps(dict(N=N, cfg=cfg, **{k: r[k] for k in ("rows", "fp32_exact", "bf16_exact", "fault",
                                                                      "cycles_last_row", "exact")})), flush=True)
        # the same x vectors (same seed) in every configuration: batched position p == serial position p == golden
        same = all(res[c]["_rows"].get(t, (None,))[:2] == v[:2] for c in ("batched", "batched_x2", "serial_nv1")
                   for t, v in res["serial"]["_rows"].items())
        for r in res.values():
            r.pop("_rows")
        s1, s5, b5, w5 = (res[c]["cycles_last_row"] for c in ("single", "serial", "batched", "batched_x2"))
        cases.append(dict(N=N, NB=2, head_rows=[HEAD_R0, HEAD_R0 + R], K=4096, configs=res,
                          batched_rows_equal_serial=same,
                          batched_over_serial=round(b5 / s5, 4), batched_over_single=round(b5 / s1, 4),
                          serial_over_single=round(s5 / s1, 4), batched_x2_over_serial=round(w5 / s5, 4),
                          batched_x2_over_single=round(w5 / s1, 4)))
    rec = dict(schema="opentallas.dsrom-dspark-batched-head-rtl.v1",
               verdict="PASS" if all(all(r["exact"] for r in c["configs"].values()) and c["batched_rows_equal_serial"]
                                     for c in cases) else "FAIL",
               lever="L2 batched head: the 5 DSpark slot rows' lm_head matvecs on one ROM sweep",
               golden_dependency=dep,
               element=dict(module="ot_v41_rom_elem_nv_w10", params=dict(NV=GAMMA, FAST=1, PP=1, BP=2, MTP=1, NB=2,
                                                                         NCH=24, XFB=8, OQ=8)),
               gate="tools/w10_validation/rtl_v41_rom_array.py (bound by this tool; x random BF16, golden G.mv chunk8)",
               checkpoint_revision=SNAP.name, checkpoint_header_sha256=ck.pins, gamma=GAMMA, cases=cases,
               source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                            text=True).stdout.strip(),
               source_sha256={p: sha(ROOT / p) for p in
                              [ELEM_NV, *RTL0, TB0, *gate.RTL_FAST,
                               "tools/dsrom_dspark_batched_head_rtl.py", "tools/w10_validation/rtl_v41_rom_array.py",
                               "tools/w10_validation/v41_rom_ksplit_bankmap.py", "tools/hdc_golden_v41.py"]})
    print(json.dumps({k: rec[k] for k in ("verdict",)} | {"cases": [{k: c[k] for k in (
        "N", "batched_over_serial", "batched_over_single", "serial_over_single", "batched_x2_over_serial",
        "batched_x2_over_single", "batched_rows_equal_serial")}
        for c in cases]}, indent=1))
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + "\n")
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
