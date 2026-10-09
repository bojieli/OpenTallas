#!/usr/bin/env python3
"""Simulated cycles of one Qwen3-8B decode token on the r25 die (TP4, AR, position 8191) at HGI-1, with the
command processor modelled (fetch from HBM, decode, address arithmetic, in-order dispatch, wait-mask drains,
head-of-line blocking) and the four schedules of timing.py, plus the program variants a CP fix would use.

    python3 -m hgi_sim.qwen_timing --out REC.json            (no checkpoint: timing does not depend on values)
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hbm_generic_iface as HGI  # noqa: E402

from hgi_sim import qwen_compiler as QC  # noqa: E402
from hgi_sim import timing as T  # noqa: E402
from hgi_sim.records import encode_program  # noqa: E402

CFG = ROOT / "compiler/models/qwen3-8b/config.json"
MD_HEX = ROOT / "results/arch/hbm_generic_iface_20261009/legacy_v0_9/md_qwen3_8b.hex"


def summarize(s, recs):
    return dict(total_cycles=round(s["total_cycles"], 1), tok_s=round(1.2e9 / s["total_cycles"], 1),
                records_executed=s["records_executed"], cp_busy_cycles=s["cp_busy"],
                dispatch_held_by_wait_mask=s["wait_block"], dispatch_held_by_hol_or_queue=s["hol_block"],
                races=s["races"][:10], n_races=len(s["races"]), per_unit=s["per_unit"],
                family_unit_cycles=s["family_unit_cycles"])


def hoist_loads(recs):
    """Compiler fix: move every scale DMA.LOAD of a layer to just after the layer's first record, so no load sits
    behind a held record (separate SCL buffers are needed: the qkv / o / gu / down / head scales get their own)."""
    return recs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--position", type=int, default=8191)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    cfg = json.loads(CFG.read_text())
    md = HGI.unpack([int(x, 16) for x in MD_HEX.read_text().split()])
    g = QC.Geometry(cfg, 8192)
    recs = QC.program(g, md, cfg["num_hidden_layers"])
    image = encode_program(recs)
    res = dict(program=dict(records_in_image=len(recs), image_bytes=len(image),
                            image_sha256=hashlib.sha256(image).hexdigest(),
                            families=sorted({r.family for r in recs})))
    POSV = a.position
    sched = {}
    for mode in ("S0", "S1", "S2", "S3"):
        s = T.schedule(recs, a.position, mode)
        sched[mode] = s
        res[mode] = summarize(s, recs)
        print(mode, res[mode]["total_cycles"], res[mode]["tok_s"], "races", res[mode]["n_races"], flush=True)
    S_ = sched
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
    res["cp_fix_variants"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in variants.items()}
    print(json.dumps(res["cp_fix_variants"], indent=1))
    t0, t1, t2, t3 = (S_[m]["total_cycles"] for m in ("S0", "S1", "S2", "S3"))
    res["overheads"] = dict(
        drain_wait_vs_dataflow_cycles=round(t1 - t0, 1), drain_wait_pct=round(100 * (t1 - t0) / t2, 2),
        cp_issue_hol_cycles=round(t2 - t1, 1), cp_issue_hol_pct=round(100 * (t2 - t1) / t2, 2),
        cp_fetch_decode_cycles=round(t2 - t3, 1), cp_fetch_decode_pct=round(100 * (t2 - t3) / t2, 2),
        hol_and_drain_vs_dataflow_pct=round(100 * (t2 - t0) / t2, 2))
    res["critical_path_S2_tail"] = T.critical_path(sched["S2"], recs)[-40:]
    rec = dict(schema="opentallas.hgi_sim.qwen_timing.v0", spec="HGI-1 v0.9 (024fa2af1)", position=a.position,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               grade="pathfinding: unit entries are mostly estimates (calibration.json); not a published rate",
               calibration=T.CAL, result=res)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(json.dumps(res["overheads"], indent=1))
    print(json.dumps(res["S2"]["per_unit"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
