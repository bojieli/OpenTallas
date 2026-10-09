#!/usr/bin/env python3
"""DeepSeek-V4.1-Flash 1M decode token (the executed TP-96 program, results/rtl/dshbm_baseline_measured_20261004/
program.json) as an HGI-1 record stream for one die, scheduled with the command processor modelled.

Lowering (spec section 3.8 native engine ops; one record per program op):
  mv            SM.MATVEC fmt 0 / 1 / 2 (BF16 / FP8 / FP4 block dot); A x (VM), B weights (HBM), O (VM)
  hc_mixes      HC.HC_MIX                 hc_pre_norm / final_norm   FUSED.HC_PRE_NORM     hc_post  FUSED.HC_POST
  index_q / index_scores / topk_local     IDX.INDEX_Q / INDEX_SCORES / TOPK
  route  IDX.TOPK;  cand_local / cand_apply / cand_mask   IDX.SELECT (param = sub-function)
  attend        ATT.QK (the tile job) + SU.VOP (the fused softmax / PV-normalise / inverse-RoPE chain)
  q_norm_kv_row / q_rope / router_act / moe_sum / compressor / engram_mix   SU.VOP (one record a fused chain)
  swiglu        SFU.GLU                   argmax_local  ARGMAX.LOCAL
  engram_fetch / expert_fetch             DMA.LOAD
  all_gather / kv_gather  COLL.ALL_GATHER    all_reduce  COLL.ALL_REDUCE_SUM    topk_merge  COLL.TOPK_MERGE /
  ARGMAX_MERGE
`wait` masks from region hazards (buffer names -> VM extents), as the Qwen compiler does.

Unit costs are the DS composition's own (tools/dshbm_1m_allmeasured.walk, every adapter at the target clocks): each
op is priced by the walk alone (minus the walk's empty-program baseline), so the S2 schedule here differs from the
published 460.05 us walk ONLY by the command processor, the wait-mask drains and the overlap the walk does not credit.
Pricing notes: the walk prices the SwiGLU chain once a layer (all 7 slots on one SU pass) -> slot 0 carries it;
hc_mixes is the full HCP + Sinkhorn time on the HC unit (the walk charges only its excess over the body: here the
schedule decides the overlap).

    python3 -m hgi_sim.ds_hgi --out REC.json         (from tools/; seconds)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import timing as T  # noqa: E402
from hgi_sim.qwen_compiler import Builder  # noqa: E402
from hgi_sim.records import MDesc, Rec, encode_program  # noqa: E402

PROGRAM = ROOT / "results/rtl/dshbm_baseline_measured_20261004/program.json"
FMT = {"fp8": (1, "FP8E4M3", 1.0), "fp4": (2, "FP4E2M1", 0.5), "bf16": (0, "BF16", 2.0)}
LOCAL_UNIT = {"hc_mixes": ("HC", "HC_MIX"), "hc_pre_norm": ("FUSED", "HC_PRE_NORM"),
              "final_norm": ("FUSED", "HC_PRE_NORM"), "hc_post": ("FUSED", "HC_POST"),
              "index_q": ("IDX", "INDEX_Q"), "index_scores": ("IDX", "INDEX_SCORES"),
              "topk_local": ("IDX", "TOPK"), "route": ("IDX", "TOPK"), "cand_local": ("IDX", "SELECT"),
              "cand_apply": ("IDX", "SELECT"), "cand_mask": ("IDX", "SELECT"), "swiglu": ("SFU", "GLU"),
              "argmax_local": ("ARGMAX", "LOCAL"), "engram_fetch": ("DMA", "LOAD")}
SUB = {"route": 6, "cand_local": 1, "cand_apply": 2, "cand_mask": 3}
TP = 96
C3B = [False]


class VMAlloc:
    SIZE = 32768                      # every named buffer gets its own extent (DS buffers are <= 32,768 words)

    def __init__(self):
        self.base, self.cur = {}, 0

    def __call__(self, name, n=0):
        if name not in self.base:
            self.base[name] = self.cur
            self.cur += self.SIZE
        return self.base[name]


def lower(prog, die=0):
    from hgi_sim import ds
    b = Builder(None)
    vm = VMAlloc()
    hbm = [1 << 34]
    io = {k: v for k, v in ds.DS_FN.items()}

    def V(name, n):
        return MDesc(space="VM", fmt="FP32", base=vm(name, n), n=n)

    def H(fmt, n, m):
        base = hbm[0]
        es = {"FP8E4M3": 1, "FP4E2M1": 1, "BF16": 2}[fmt]
        nb = n * m * es
        hbm[0] += -(-nb // 4096) * 4096 + 4096
        return MDesc(space="HBM", fmt=fmt, base=base, n=n if fmt != "FP4E2M1" else n // 2, m=m,
                     stride=n * es if fmt != "FP4E2M1" else n // 2)
    def implicit(r, rd, wr):
        r.implicit = [("r", ("VM", vm(n), vm(n) + VMAlloc.SIZE)) for n in rd] + \
                     [("w", ("VM", vm(n), vm(n) + VMAlloc.SIZE)) for n in wr]
    _add = b.add

    def add(r, rd, wr):
        implicit(r, rd, wr)
        return _add(r, rd, wr)
    b.add = add
    for lay in prog["layers"]:
        L = lay["layer"]
        for op in lay["ops"]:
            k = op["kind"]
            src = dict(layer=L, op=op)
            if k == "mv":
                fp, fmt, _ = FMT[op["fmt"]]
                r0, r1 = op["rows"][die]
                rows = max(1, r1 - r0)
                x = op["x"]
                xin = "ea" if x.startswith("ea") and x[2:].isdigit() else x
                bdesc = H(fmt, op["k"], rows)
                slot = isinstance(op["w"], list) and len(op["w"]) == 2 and isinstance(op["w"][0], int)
                if slot and op["w"][0] < 6 and C3B[0]:      # routed expert: indexed descriptor on the router id word
                    bdesc.indexed, bdesc.dyn_mul = 1, 1 << 20
                dd = dict(A=V(xin, op["k"] if xin != "ea" else 7 * 2304), B=bdesc, O=V(op["out"], op["n"]))
                if bdesc.indexed:
                    dd["I"] = MDesc(space="VM", fmt="U32", base=vm("route_ids", 8) + op["w"][0], n=1)
                r = Rec("SM", "MATVEC", param=fp, desc=dd,
                        tag=op["tag"], family="mv." + op["fn"])
                r.src = src
                b.add(r, [xin] + (["expert_w"] if slot else []), [op["out"]])
            elif k == "local":
                fn = op["fn"]
                _, rd, wr = io[fn]
                fill = dict(w=op.get("which", ""), slot=op.get("slot", 0))
                rd = [x.format(**fill) for x in rd]
                wr = [x.format(**fill) for x in wr]
                if fn == "attend":
                    r = Rec("ATT", "QK", param=1, desc=dict(A=V("q_own", 512), O=V("att_s", 1024)), tag="attend.tile",
                            family="attend")
                    r.src = dict(src, part="tile")
                    b.add(r, ["q_own", "sel_rows", "win_new"], ["att_s"])
                    r = Rec("SU", "VOP", sut={}, desc=dict(A=V("att_s", 1024), O=V("o_own", 512)),
                            tag="attend.chain", family="attend")
                    r.src = dict(src, part="chain")
                    b.add(r, ["att_s"], wr)
                    continue
                unit, uop = LOCAL_UNIT.get(fn, ("SU", "VOP"))
                desc = dict(A=V(rd[0] if rd else "zero", 1024), O=V(wr[0], 1024)) if unit != "DMA" else \
                    dict(A=H("BF16", 6144, 1), O=V(wr[0], 6144))
                r = Rec(unit, uop, param=SUB.get(fn, 0), sut={} if unit == "SU" else None, desc=desc,
                        tag=op["tag"], family=fn)
                r.src = src
                b.add(r, rd, wr)
            elif k in ("all_gather", "all_reduce", "topk_merge", "kv_gather"):
                uop = {"all_gather": "ALL_GATHER", "kv_gather": "ALL_GATHER", "all_reduce": "ALL_REDUCE_SUM",
                       "topk_merge": "ARGMAX_MERGE" if op.get("what") == "argmax" else "TOPK_MERGE"}[k]
                rd = op.get("bufs") or [op.get("buf") or (f"{op.get('what')}_v" if k == "topk_merge" else "sel")]
                if k == "kv_gather":
                    rd = ["sel", "kvstore"]
                wr = rd if k == "all_gather" else ([op["out"]] if k == "all_reduce" else
                                                   (["sel_rows"] if k == "kv_gather" else [f"{op.get('what')}_m"]))
                r = Rec("COLL", uop, desc=dict(A=V(rd[0], 1024), O=V(wr[0], 1024)), tag=op["tag"], family=k)
                r.src = src
                b.add(r, rd, wr)
            elif k == "expert_fetch":
                r = Rec("DMA", "LOAD", desc=dict(A=H("FP4E2M1", 5120, 288), O=V("expert_w", 64)), tag=op["tag"],
                        family="expert_fetch")
                r.src = src
                b.add(r, ["route_ids"], ["expert_w"])
    prev = None
    for r in b.recs:                      # the walk's flush groups: consecutive expert-slot matvecs, one drain
        if getattr(r, "src", None) and r.unit == "SM" and r.src["op"]["tag"].startswith("expert slot"):
            r.src["batched"] = prev is not None
            prev = r
        elif getattr(r, "src", None) and r.unit == "SFU":
            pass
        else:
            prev = None
    r = Rec("CTL", "END", tag="end", family="end")
    r.src = None
    b.add(r, [], [])
    return b.recs


class WalkCost:
    """Per-op price from the DS composition's walk (target clocks, every measured adapter)."""

    def __init__(self):
        import dshbm_1m_allmeasured as DA
        self.DA = DA
        self.sm = DA.WC.SMTable([json.loads((DA.ROOT / "results/rtl/w19_sm_real_ops.json").read_text()),
                                 json.loads((DA.BASE / "sm_real_ops.json").read_text())], "ar")
        self.su1, _, _, _ = DA.su_tables()
        self.coll, self.local, self.hbm = DA.Coll(DA.load(DA.REC / "collectives.json")), \
            DA.Local(DA.load(DA.REC / "local.json")), DA.Hbm(DA.load(DA.REC / "hbm_streams.json"))
        self.use = ("coll", "local", "hbm", "mixes")
        self.base, _ = DA.walk({"layers": []}, self.sm, self.su1, self.coll, self.local, self.hbm, use=self.use)
        self.mix_us, self.mix_how = DA.hc_mixes_us(1, DA.TARGET)
        self.cache = {}

    def op_rows(self, L, op):
        key = (L, op["id"])
        if key not in self.cache:
            t, rows = self.DA.walk({"layers": [{"layer": L, "ops": [op]}]}, self.sm, self.su1, self.coll, self.local,
                                   self.hbm, use=self.use)
            self.cache[key] = [r for r in rows if r["node"] != "hbm:embedding_row"]
        return self.cache[key]

    def __call__(self, r, dyn, L):
        if r.src is None:
            return 1.0, "estimate", "END"
        op, Lsrc = r.src["op"], r.src["layer"]
        if op.get("fn") == "hc_mixes":
            return self.mix_us * 1200, "measured", self.mix_how
        if op.get("fn") == "swiglu" and op.get("slot", 0) != 0:
            return 0.0, "measured", "SwiGLU chain priced once a layer (slot 0)"
        rows = self.op_rows(Lsrc, op)
        if op["kind"] == "mv" and op["tag"].startswith("expert slot") and r.src.get("batched"):
            rows = [x for x in rows if x["node"] != "barrier"]
            lines = [x for x in rows if x["node"].startswith("sm:")]
            if lines:
                rr, k, fmt = op["rows"], op["k"], op["fmt"]
                Rr = -(-max(r1 - r0 for r0, r1 in rr) // self.DA.WC.N_SM)
                ln, dr, _ = self.sm.op(fmt, k, Rr)
                return ln / self.DA.TARGET["sm"] * 1.2e9, "measured", "sm lines (batched, walk rule)"
        part = r.src.get("part")
        if part == "tile":
            rows = [x for x in rows if x["node"].startswith("attn:") or x["node"].startswith("hbm:")]
        elif part == "chain":
            rows = [x for x in rows if x["node"].startswith("su:")]
        us = sum(x["us"] for x in rows)
        cls = sorted({x["cls"] for x in rows}) or ["measured"]
        return us * 1200, "+".join(cls), "; ".join(x["node"] for x in rows)[:160]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    prog = json.loads(PROGRAM.read_text())
    recs = lower(prog)
    image = encode_program(recs)
    wc = WalkCost()
    walk_us, _ = wc.DA.walk(prog, wc.sm, wc.su1, wc.coll, wc.local, wc.hbm, use=wc.use)
    res = dict(program=dict(records=len(recs), image_bytes=len(image),
                            image_sha256=hashlib.sha256(image).hexdigest()),
               published_walk_us=round(walk_us, 3), published_walk_cycles=round(walk_us * 1200, 1))
    POSV = 1048575
    S = {}
    for mode in ("S0", "S1", "S2", "S3"):
        s = T.schedule(recs, 1048575, mode, cost_fn=wc)
        S[mode] = s
        res[mode] = dict(total_cycles=round(s["total_cycles"], 1), us=round(s["total_cycles"] / 1200, 3),
                         tok_s=round(1.2e9 / s["total_cycles"], 1), records_executed=s["records_executed"],
                         cp_busy_cycles=s["cp_busy"], n_races=len(s["races"]), races=s["races"][:5],
                         per_unit=s["per_unit"], family_unit_cycles=dict(list(s["family_unit_cycles"].items())[:25]))
        print(mode, res[mode]["total_cycles"], res[mode]["us"], res[mode]["tok_s"], "races", len(s["races"]),
              flush=True)
    S_ = S
    cf = {} if "qwen" in __name__ or True else {}
    variants = {}
    kw = dict(cost_fn=wc) if "wc" in dir() else {}
    variants["S2_no_wires"] = T.schedule(recs, POSV, "S2", wires=False, **kw)["total_cycles"]
    variants["SX_skip_ahead"] = T.schedule(recs, POSV, "SX", **kw)["total_cycles"]
    ro = T.reorder(recs, POSV, rebuild=T.rebuild_waits, **kw)
    sro = T.schedule(ro, POSV, "S2", **kw)
    variants["S2_compiler_reordered"] = sro["total_cycles"]
    variants["S2_compiler_reordered_races"] = len(sro["races"])
    variants["SX_compiler_reordered"] = T.schedule(ro, POSV, "SX", **kw)["total_cycles"]
    C3B[0] = True
    recs_c3b = lower(prog)
    s_c3b = T.schedule(recs_c3b, POSV, "S2", **kw)
    ls_c3b = T.schedule(T.list_schedule(recs_c3b, POSV, **kw), POSV, "S2", **kw)
    variants["S2_with_C3b_indexed_expert_descriptors"] = s_c3b["total_cycles"]
    variants["S2_list_scheduled_with_C3b"] = ls_c3b["total_cycles"]
    C3B[0] = False
    ls = T.list_schedule(recs, POSV, **kw)
    sls = T.schedule(ls, POSV, "S2", **kw)
    variants["S2_compiler_list_scheduled"] = sls["total_cycles"]
    variants["S2_compiler_list_scheduled_races"] = len(sls["races"])
    variants["S2_compiler_list_scheduled_no_wires"] = T.schedule(ls, POSV, "S2", wires=False, **kw)["total_cycles"]
    variants["S0_dataflow"] = S_["S0"]["total_cycles"]
    res["list_scheduled_program"] = dict(records=len(ls), image_sha256=hashlib.sha256(encode_program(ls)).hexdigest(),
                                         per_unit=sls["per_unit"])
    res["cp_fix_variants"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in variants.items()}
    print(json.dumps(res["cp_fix_variants"], indent=1))
    t0, t1, t2, t3 = (S_[m]["total_cycles"] for m in ("S0", "S1", "S2", "S3"))
    res["overheads"] = dict(
        drain_wait_vs_dataflow_cycles=round(t1 - t0, 1), drain_wait_pct=round(100 * (t1 - t0) / t2, 2),
        cp_issue_hol_cycles=round(t2 - t1, 1), cp_issue_hol_pct=round(100 * (t2 - t1) / t2, 2),
        cp_fetch_decode_cycles=round(t2 - t3, 1), cp_fetch_decode_pct=round(100 * (t2 - t3) / t2, 2),
        hol_and_drain_vs_dataflow_pct=round(100 * (t2 - t0) / t2, 2),
        s2_vs_published_walk_pct=round(100 * (t2 / (walk_us * 1200) - 1), 2))
    print(json.dumps(res["overheads"], indent=1))
    rec = dict(schema="opentallas.hgi_sim.ds_timing.v0", spec="HGI-1 1.0 (approved encoding)", position=1048575,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               grade="unit costs = the DS composition's (measured / measured_tu_budget / modelled rows as there); "
                     "CP entries estimates (calibration.json)", result=res, calibration_cp=T.CAL["cp"])
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
