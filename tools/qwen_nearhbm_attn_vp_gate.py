#!/usr/bin/env python3
"""Collect the verify-block near-HBM attention gate (rtl/test/nearhbm/tb_qwen_nearhbm_attn_vp.cpp runs) into one record.

    python3 tools/qwen_nearhbm_attn_vp_gate.py --res RESDIR --vectors-root ROOT --out results/.../vp_gate.json

RESDIR holds <build>__<case>__<first>.json/.rc from the run chain; <build> is h<HD>r<R>_vp<VP> (h16r = 16-lane real
arithmetic units).  Each pass runs positions first .. first+VP-1 of a verify block on one K/V stream of T = the last
position's context, each copy masked to its own context.  The record states, per p in {1, 2, 4}:
  * exactness of every position against the golden (tools/qwen_nearhbm_attn_verify_ref.py: hdc_golden at T_i);
  * measured cycles of the block: VP = 1 runs p passes (one per position, the parent engine, m_attn = 1), VP = 2 runs
    ceil(p/2) passes, VP = 4 one pass;
  * the increment per extra position against the pricing model (attention_m_attn_1 = 1,512, attention_m_attn_ge_p = 112).
"""
import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = dict(attention_m_attn_1=1512, attention_m_attn_ge_p=112,
             source="results/speculative/qwen_rom_speculation_recheck_20261003/pricing.json "
                    "(branch claude/qwen-rom-speculation-recheck-20261003) increment_per_extra_position_per_layer")


def phases(m):
    k_end, v_end = m["k_rows_served_last"], m["v_rows_served_last"]
    return dict(q_in=m["q_ready"], K_stream=k_end - m["k_rows_served_first"],
                K_to_V_gap=m["v_rows_served_first"] - k_end, V_stream=v_end - m["v_rows_served_first"],
                drain=m["pv_first_beat"] - v_end, return_hub=m["out_last"] - m["pv_first_beat"], total=m["out_last"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--res", type=Path, required=True)
    ap.add_argument("--vectors-root", type=Path, required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    runs = []
    for js in sorted(a.res.glob("*.json")):
        b, case, first = js.stem.split("__")
        m = re.match(r"h(\d+)(r|d)?r?(\d+)?_vp(\d+)", b)
        txt = js.read_text().strip()
        rc = (a.res / f"{js.stem}.rc").read_text().strip() if (a.res / f"{js.stem}.rc").exists() else None
        try:
            r = json.loads(txt.splitlines()[-1])
        except Exception:
            r = {"exact": False, "error": txt[-300:]}
        hd = int(re.match(r"h(\d+)", b).group(1))
        vp = int(b.split("_vp")[1])
        rr = int(re.search(r"r(\d+)_", b).group(1)) if re.search(r"r(\d+)_", b) else 1
        vroot = a.vectors_root / ("v16" if hd == 16 else "v128") / case
        meta = json.loads((vroot / "meta.json").read_text())
        row = dict(build=b, hd=hd, r=rr, vp=vp, fp=("real" if b.startswith("h16r") else "dpi"), case=case,
                   kind=meta["kind"], ctx=meta["ctx"], p=meta["p"], first=int(first), rc=rc,
                   exact=bool(r.get("exact")), per_position_mismatches=r.get("per_position_mismatches"),
                   fault=r.get("fault"), cycles_total=r.get("cycles_total"), mask_ctx=r.get("mask_ctx"),
                   unmasked_differs=meta.get("unmasked_differs"))
        if r.get("marks"):
            row["phases"] = phases(r["marks"])
        runs.append(row)
    # block cycles per (build family hd/r, case, p)
    by = defaultdict(dict)
    for x in runs:
        by[(x["hd"], x["r"], x["fp"], x["case"])].setdefault(x["vp"], []).append(x)
    blocks = []
    for (hd, rr, fp, case), d in sorted(by.items()):
        ent = dict(hd=hd, r=rr, fp=fp, case=case)
        for vp, xs in sorted(d.items()):
            p = xs[0]["p"]
            for pp in (1, 2, 4):
                if pp > p:
                    continue
                passes = [x for x in xs if x["first"] < pp and x["first"] + vp <= pp]
                need = -(-pp // vp) if vp <= pp else None
                if need is None or len(passes) != need:
                    continue
                ent.setdefault(f"p{pp}", {})[f"vp{vp}"] = dict(
                    passes=need, exact=all(x["exact"] for x in passes),
                    cycles=sum(x["cycles_total"] or 0 for x in passes),
                    pass_cycles=[x["cycles_total"] for x in passes])
        blocks.append(ent)
    exact_all = all(x["exact"] for x in runs) and bool(runs)
    increments = []
    for e in blocks:
        p1 = e.get("p1", {}).get("vp1", {}).get("cycles")
        for pp in (2, 4):
            for vk, v in e.get(f"p{pp}", {}).items():
                if p1:
                    increments.append(dict(hd=e["hd"], r=e["r"], case=e["case"], p=pp, lane_sets=vk,
                                           block_cycles=v["cycles"], p1_cycles=p1,
                                           per_extra_position=round((v["cycles"] - p1) / (pp - 1), 1)))
    rec = dict(schema="qwen-nearhbm-attn-vp-gate.v1", source_commit=a.source_commit,
               verdict="PASS" if exact_all else "FAIL", runs=len(runs), exact_runs=sum(x["exact"] for x in runs),
               model=MODEL, increments=increments, blocks=blocks, rows=runs,
               note=("Each lane set in the bench has its own q link, hub and return link; the copies share only the HBM "
                     "K/V stream (lockstep checked: fault bit 5).  A design sharing the q / return links would add their "
                     "serialisation per extra position (the model's q 40 + return 72)."))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdict=rec["verdict"], runs=rec["runs"], exact=rec["exact_runs"],
                          increments=[i for i in increments if i["hd"] == 128]), indent=1))


if __name__ == "__main__":
    main()
