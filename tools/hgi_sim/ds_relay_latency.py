#!/usr/bin/env python3
"""H-MTP2 / H-DIE die-growth study: the tok/s cost of the extra on-die relay stages when the HBM die grows from
660 mm2 (v5 carry) to ~790 mm2 (core4_sfu2_su2825, claude/hdie-v6b).

METHOD.  One relay stage = one 1.2 GHz cycle of fixed latency on a static fixed-cycle pipeline: it does not change a
record's streaming II, only its fill latency.  Every record of the DS native programme (the compiled AR token, the
batched verify(P = 6), the compiled R-row DSpark draft) gets  sum over link classes of  delta_stages(class) x
crossings(record, class)  cycles added to its unit cost (a wrapped ds_mtp_verify.cost_fn), and the SAME S2 schedule
(command processor, wait masks, per layer segment) is re-run: the added latency is exposed only where the schedule
is serially dependent.  delta_stages = bit-weighted relay stages per class (pin-to-pin lane model, 480 um reach,
v6_eval.py), v6 eval minus v5carry eval.

CROSSINGS per record (die graph tools/hbm_globalfp_graph.py; a request + response pair on one class pays twice):
  SM.MATVEC     SM_HBM x2 (req 44 b + rsp 1088 b, weight first access) || SM_X x2 (x request + data) -> SM_OUT x1
                -> VM_HUB x1 (hub -> bank).  nominal: weight fetch and x load overlap (max of the two legs);
                upper: serial sum.
  ATT.* (option B, on the SM)   KV_DESC x1 + SM_HBM x2 (KV lines) || SM_X x2 (q / P) -> SM_OUT x1 -> VM_HUB x1
  DMA.LOAD / swap-in            VM_HBM x1 (request) + HBM_VM x1 (data) + VM_HUB x1 (delivery)
  DMA.STORE / KVWB / swap-out   VM_HUB x2 (bank read) + VM_HBM x1   (posted: exposed only through waits)
  DMA.FENCE                     VM_HBM x1 + HBM_VM x1
  COLL.* gather-class           COLL_VM x2 (read) + COLL_EP + EP_SERDES (tx) + EP_SERDES + COLL_EP (rx) + COLL_VM x1
                                (write) + COLL_RING x1 nominal / x2 upper (2x2 quadrant ring, diameter 2)
  COLL.ALL_REDUCE / GROUP_REDUCE_MCAST   the off-die legs and the ring twice (two crossings, perf.coll_cycles)
  IDX.*         IDX_VM x2 + IDX_INT x4 (operand -> query -> score -> select -> link) + IDX_COLL x1 + COLL_VM x1
  HC.*, FUSED.HC_PRE_NORM / HC_POST   HC_CORE x2 (port group <-> core) + HC_ENG x2 (tap <-> NE engine)
  FUSED.QDQ*    QUANT_VM (0 stages)   FUSED other: SU_CORE x2
  SU.VOP        SU_CORE x2 (+ SFU_CORE x2 when the template uses the SFU)    SFU.*: SFU_CORE x2
  ARGMAX.*      SU_CORE x2      CTL.*: 0      LG_SU/HC/SFU and HBM_K: 0 stages (both evals)

    python3 -m hgi_sim.ds_relay_latency --out REC.json [--jobs N]        (from tools/)
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import ds_mtp_verify as V  # noqa: E402

V6 = "results/arch/hbm_die_v15/core4_sfu2_su2825/eval.json"
V5 = "results/arch/hbm_die_v15/v6_plan_1016/v5carry/eval.json"
BRANCH = "origin/claude/hdie-v6b"
# the DS MTP design point that meets the 3,500 screen with the least area (ds_mtp_rows smallest_meeting_target)
DESIGN_ITEMS = ["COLL", "FUSED", "HC", "SU_DMA", "IDX", "ATT", "SM_K2"]


def stages():
    import os
    if os.environ.get("OT_RELAY_STAGES"):
        return json.loads(Path(os.environ["OT_RELAY_STAGES"]).read_text())
    out = {}
    for tag, p in (("v6", V6), ("v5", V5)):
        try:
            d = json.loads((ROOT / p).read_text())
            src = p
        except FileNotFoundError:
            d = json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BRANCH}:{p}"]))
            src = f"{BRANCH}:{p}"
        out[tag] = dict(source=src, die_mm2=d["die_mm2"], per_class={k: v["stages_bw"] for k, v in d["per_class"].items()})
    return out


def crossings(r, upper=False):
    """{class: crossings} of one record (see module doc)"""
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    u, o = op.split(".", 1)
    tag = r.tag or ""
    if op == "DMA.SWAP":
        o = "LOAD" if "in" in tag.split()[-1] else "STORE"
    if u == "SM" or u == "ATT":
        c = dict(SM_HBM=2, SM_X=2, SM_OUT=1, VM_HUB=1)
        if u == "ATT":
            c["KV_DESC"] = 1
        c["_par"] = not upper            # weight / KV fetch leg || x leg
        return c
    if u == "DMA":
        if o == "LOAD":
            return dict(VM_HBM=1, HBM_VM=1, VM_HUB=1)
        if o == "FENCE":
            return dict(VM_HBM=1, HBM_VM=1)
        return dict(VM_HUB=2, VM_HBM=1)
    if u == "COLL":
        k = 2 if o in ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST") else 1
        return dict(COLL_VM=3, COLL_EP=2 * k, EP_SERDES=2 * k, COLL_RING=(2 if upper else 1) * k)
    if u == "IDX":
        return dict(IDX_VM=2, IDX_INT=4, IDX_COLL=1, COLL_VM=1)
    if u == "HC" or (u == "FUSED" and o.startswith("HC_")):
        return dict(HC_CORE=2, HC_ENG=2)
    if u == "FUSED":
        return {} if o.startswith("QDQ") else dict(SU_CORE=2)
    if u == "SU":
        sut = getattr(r, "sut", None)
        c = dict(SU_CORE=2)
        if isinstance(sut, dict) and sut.get("sfu"):
            c["SFU_CORE"] = 2
        return c
    if u == "SFU":
        return dict(SFU_CORE=2)
    if u == "ARGMAX":
        return dict(SU_CORE=2)
    return {}


def added(r, delta, upper=False, only=None):
    c = dict(crossings(r, upper))
    par = c.pop("_par", False)
    d = {k: n * delta.get(k, 0.0) for k, n in c.items() if only is None or k in only}
    if par:
        fetch = d.pop("SM_HBM", 0.0) + d.pop("KV_DESC", 0.0)
        x = d.pop("SM_X", 0.0)
        return sum(d.values()) + max(fetch, x)
    return sum(d.values())


_ORIG_CF = V.cost_fn
_KNOB = {}


def cost_fn(scale=None):
    base = _ORIG_CF(scale)
    if not _KNOB:
        return base
    delta, upper, only = _KNOB["delta"], _KNOB["upper"], _KNOB["only"]

    def cf(r, dyn, L):
        c, g, how = base(r, dyn, L)
        return c + added(r, delta, upper, only), g, how
    return cf


V.cost_fn = cost_fn

_CTX = {}


def _ctx():
    if "recs" not in _CTX:
        from hgi_sim import ds_mtp_rows as R    # needs physical/ref_tile/smh_bdc_ref_p50 (BDC LEF pin)
        _CTX["R"] = R
        _CTX["d"], _CTX["recs"], _CTX["cf"] = V.load()
        bm = json.loads(V.BMODEL.read_text())
        _CTX["bex"] = {T_: dict(qk=v["qk"], pv=v["pv"]) for T_, v in bm["exposed"]["per_record"].items()}
        _CTX["bcomp"] = bm["measured_comp"]
    return _CTX


def compile_case(case):
    c = _ctx()
    if case == "AR":
        return V.compile_verify(c["recs"], c["cf"], 1, att="B", bmodel=c["bex"])[0]
    if case == "MTP_headline":
        return V.compile_verify(c["recs"], c["cf"], 6, sm_mode="pport", swap=True, att="B", bmodel=c["bex"])[0]
    if case == "MTP_design":
        cfg = c["R"].cfg_of(DESIGN_ITEMS)
        return V.compile_verify(c["recs"], c["cf"], 6, sm_mode=cfg["sm_mode"], att="B", bmodel=c["bex"],
                                bcomp=c["bcomp"], swap=cfg["swap"], rows=cfg["rows"], sm_k=cfg["sm_k"],
                                att_k=cfg["att_k"])[0]
    raise KeyError(case)


def _job(job):
    name, case, knob = job
    _KNOB.clear()
    if knob:
        _KNOB.update(knob)
    c = _ctx()
    if case == "draft_design":
        from hgi_sim import ds_mtp_draft as D
        d = D.draft_step(c["R"].cfg_of(DESIGN_ITEMS), None)
        return name, dict(draft_cycles=d["draft_cycles"], seed_cycles=d["seed_cycles"])
    prog = compile_case(case)
    r = V.run(prog, None)
    out = dict(cycles=r["cycles"], records=r["records"])
    if not knob:      # crossing census of the base programme
        st_ = stages()
        stg = {k: st_["v6"]["per_class"][k] - st_["v5"]["per_class"].get(k, 0.0) for k in st_["v6"]["per_class"]}
        cen, tot = {}, {}
        for x in prog:
            cr = dict(crossings(x))
            cr.pop("_par", None)
            for k, n in cr.items():
                cen[k] = cen.get(k, 0) + n
            tot[x.orig_op] = tot.get(x.orig_op, 0) + 1
        out["crossings"] = cen
        out["records_by_op"] = tot
        out["sum_added_nominal"] = round(sum(added(x, stg) for x in prog), 1)
    return name, out


_KNOB_CENSUS = {}

GROUPS = {
    "SM (SM_HBM, SM_X, SM_OUT, KV_DESC)": ("SM_HBM", "SM_X", "SM_OUT", "KV_DESC"),
    "VM/DMA (VM_HUB, HBM_VM, VM_HBM)": ("VM_HUB", "HBM_VM", "VM_HBM"),
    "COLL (COLL_VM, COLL_RING, COLL_EP, EP_SERDES)": ("COLL_VM", "COLL_RING", "COLL_EP", "EP_SERDES"),
    "IDX (IDX_VM, IDX_INT, IDX_COLL)": ("IDX_VM", "IDX_INT", "IDX_COLL"),
    "HC (HC_CORE, HC_ENG)": ("HC_CORE", "HC_ENG"),
    "SU/SFU (SU_CORE, SFU_CORE)": ("SU_CORE", "SFU_CORE"),
}


def main():
    import multiprocessing as mp
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    st = stages()
    dl = lambda t: {k: round(st[t]["per_class"][k] - st["v5"]["per_class"].get(k, 0.0), 3) for k in st[t]["per_class"]}
    delta = dl("v6")
    delta_head = dl("v6_head") if "v6_head" in st else None
    _KNOB_CENSUS["delta"] = delta
    jobs = []
    for case in ("AR", "MTP_headline", "MTP_design"):
        jobs.append((f"{case}|base", case, None))
        jobs.append((f"{case}|v6_nominal", case, dict(delta=delta, upper=False, only=None)))
        jobs.append((f"{case}|v6_upper", case, dict(delta=delta, upper=True, only=None)))
        if delta_head:
            jobs.append((f"{case}|v6head_nominal", case, dict(delta=delta_head, upper=False, only=None)))
        jobs.append((f"{case}|plus4_all", case, dict(delta={k: 4.0 for k in delta}, upper=False, only=None)))
        for g, cl in GROUPS.items():
            jobs.append((f"{case}|group:{g}", case, dict(delta=delta, upper=False, only=set(cl))))
            jobs.append((f"{case}|plus4:{g}", case, dict(delta={k: 4.0 for k in cl}, upper=False, only=set(cl))))
    for v in ("base", "v6_nominal", "v6_upper"):
        kn = None if v == "base" else dict(delta=delta, upper=v == "v6_upper", only=None)
        jobs.append((f"draft_design|{v}", "draft_design", kn))
    with mp.Pool(a.jobs) as pool:
        qw = pool.apply_async(qwen_runs, (st,))
        res = dict(pool.map(_job, jobs, chunksize=1))
        qwen = qw.get()
    # compose: headline MTP = verify + (row-serial draft + seed + mh stores) x AR ratio + control (ds_mtp_verify.compose)
    ref = json.loads((ROOT / "results/arch/hbm_mtp_1015/ds_mtp_verify_1M.json").read_text())
    row = next(t for t in ref["steps"]["table"] if t["case"] == "B_exposed|verify6|pport|swap|fixed")
    extra_h = row["draft_cycles"] + row["seed_cycles"] + row["mh_store_cycles"]
    dref = json.loads((ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json").read_text())
    smt = dref["smallest_meeting_target"]["fixed"]
    mh_d = smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]   # mh stores + control
    variants = sorted({k.split("|", 1)[1] for k in res if k.startswith("AR|")})
    table = {}
    for v in variants:
        ar = res[f"AR|{v}"]["cycles"]
        k = ar / res["AR|base"]["cycles"]
        hs = res[f"MTP_headline|{v}"]["cycles"] + extra_h * k + row["control_cycles"]
        dk = f"draft_design|{v}" if f"draft_design|{v}" in res else None
        if dk:
            dd = res[dk]["draft_cycles"] + res[dk]["seed_cycles"]
            dbasis = "compiled R-row draft re-timed"
        else:
            dd = (res["draft_design|base"]["draft_cycles"] + res["draft_design|base"]["seed_cycles"]) * \
                res[f"MTP_design|{v}"]["cycles"] / res["MTP_design|base"]["cycles"]
            dbasis = "draft scaled by the design verify ratio"
        ds = res[f"MTP_design|{v}"]["cycles"] + dd + mh_d
        table[v] = dict(ar_cycles=ar, ar_tok_s=round(V.CLK / ar, 1),
                        mtp_headline_step=round(hs, 1), mtp_headline_tok_s=round(V.TAU * V.CLK / hs, 1),
                        mtp_design_step=round(ds, 1), mtp_design_tok_s=round(V.TAU * V.CLK / ds, 1),
                        design_draft_basis=dbasis)
    b = table["base"]
    for v, t in table.items():
        t["d_ar_pct"] = round(100 * (t["ar_tok_s"] / b["ar_tok_s"] - 1), 3)
        t["d_mtp_headline_pct"] = round(100 * (t["mtp_headline_tok_s"] / b["mtp_headline_tok_s"] - 1), 3)
        t["d_mtp_design_pct"] = round(100 * (t["mtp_design_tok_s"] / b["mtp_design_tok_s"] - 1), 3)
    rec = dict(schema="opentallas.hbm_mtp_1015.die_growth_relay.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, stages=st, delta_stages=delta, delta_stages_v6_head=delta_head, design_items=DESIGN_ITEMS,
               reference=dict(ar_tok_s_ref=row["ar_tok_s"], mtp_headline_ref=row["mtp_tok_s"],
                              mtp_design_ref=smt["mtp_tok_s"]),
               table=table, qwen_ar=qwen, runs=res)
    print(json.dumps(table, indent=1))
    print(json.dumps({k: v for k, v in qwen.items() if k != "records_by_op"}, indent=1))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1) + "\n")
    return 0



def qwen_runs(st, position=8191):
    """Qwen3-8B AR on the generic HBM die (TP4, HGI-1 programme of hgi_sim.qwen_compiler, timing.cost unit prices,
    S2 with the command processor; the hgi_sim.qwen_timing basis -- pathfinding grade) with the same per-record relay
    latency rule.  Qwen attention records are ATT.* (priced on the ATT table) and get the option-B SM crossings."""
    from hgi_sim import qwen_timing as QT
    from hgi_sim import timing as T
    cfg = json.loads(QT.CFG.read_text())
    recs = QT.QC.program(QT.QC.Geometry(cfg, 8192), QT.QC.qwen_params(cfg), cfg["num_hidden_layers"])
    dl = lambda t: {k: round(st[t]["per_class"][k] - st["v5"]["per_class"].get(k, 0.0), 3) for k in st[t]["per_class"]}
    variants = dict(base=None, v6_nominal=(dl("v6"), False), v6_upper=(dl("v6"), True),
                    plus4_all=({k: 4.0 for k in dl("v6")}, False))
    if "v6_head" in st:
        variants["v6head_nominal"] = (dl("v6_head"), False)
    out = {}
    for v, kn in variants.items():
        if kn is None:
            cf = T.cost
        else:
            def cf(r, dyn, L, kn=kn):
                c, g, how = T.cost(r, dyn, L)
                return c + added(r, kn[0], kn[1]), g, how
        s = T.schedule(recs, position, "S2", cost_fn=cf)
        out[v] = dict(cycles=round(s["total_cycles"], 1), tok_s=round(1.2e9 / s["total_cycles"], 1))
    from collections import Counter
    out["records_by_op"] = dict(Counter(f"{r.unit}.{r.op}" for r in recs))
    out["sum_added_nominal_per_record"] = round(sum(added(r, dl("v6")) for r in recs), 1)
    for v in out:
        if isinstance(out[v], dict) and "tok_s" in out[v]:
            out[v]["d_pct"] = round(100 * (out[v]["tok_s"] / out["base"]["tok_s"] - 1), 3)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
