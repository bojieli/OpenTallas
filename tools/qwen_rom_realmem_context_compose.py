#!/usr/bin/env python3
"""Compose the REAL_MEM Qwen3-8B ROM token at long context (P4095 / P8191) from one measured layer.

Owner rule (simulate the minimum component): the 36 decoder layers have one shape, so each position runs only
  * an isolated L0 (HBM model from reset) with the per-cycle sequencer trace (RT_PROGRESS=1: one `progress` line
    per cycle carrying the die's segment program base), and
  * a chained L0,L1,L2 (h_start between layers, the token K/V write-backs of the previous layer in flight and the
    HBM refresh calendar running), which gives the steady chained layer;
both entered from the GPU ISA golden (tools/qwen_rom_position_oracle_gpu.py, 3 layers over the prompt), every die's
X and every written-back token K/V checked bit-exactly by tools/qwen_rom_rt_token_w12_rm.py.  E (embedding) and the
head carry no KV term and are taken unchanged from the P255 full-token record.  The token is composed exactly as
the P255 record composes it:
    7 + E + (L0_isolated - 1) + 35 x chained_steady + (head - 1) + 37 stage switches
with chained_steady the mean of the chained L1/L2 (max as the bound).  The attention share is read from the
trace: segment 0 of the layer program (pc 0..17) is RMS, QKV, q/k norms + RoPE, the token K/V write, QK, softmax,
PV and the O projection with its all-reduce; segment 1 (pc 18..25) is the residual, RMS, gate/up, SiLU and down with
its all-reduce; segment 2 (pc 26..28) the final residual.  Only QK/softmax/PV scale with P,
so the context-proportional cycles come from the per-position segment-0 cycles (linear fit over the positions).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

# segment descriptors of the img256 layer program (segments.hex: bases 0, 0x12, 0x1a); the trace reports the base of the
# segment being sequenced, and the all-reduce that ends a segment is waited inside it.
SEG_BASES = (0, 18, 26)
SEG_NAMES = ("attn_block_pc0_17", "mlp_block_pc18_25", "residual_pc26_28")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def job(d: Path):
    r = json.loads((d / "result.json").read_text())
    log = (d / "w" / "token.log").read_text()
    ok = (r["status"] == "pass" and all(v["mismatches"] == 0 for v in r["layer_x_checks"].values())
          and all(v["k_mismatches"] == 0 and v["v_mismatches"] == 0 for v in r["token_kv_writeback_checks"].values()))
    faults = {m.group(1): [int(x) for x in m.groups()[1:]] for m in
              re.finditer(r"STAGE (\S+) done .*?seq_fault=(\d+) core_fault=(\d+) coll_fault=(\d+)", log)}
    keys = ("fill_cycles", "fill_sectors", "wr_sectors", "stall_kv", "stall_drain", "stall_bridge", "wr_lat_max")
    st = {n: {"cycles": s["cycles"], "faults": faults.get(n),
              "memory_die0": {k: s["memory"]["die0"].get(k) for k in keys},
              "memory_dies_identical": len({json.dumps(v, sort_keys=True) for v in s["memory"].values()}) == 1}
          for n, s in r["stages"].items()}
    ok = ok and all(f == [0, 0, 0] for f in faults.values()) and set(faults) == set(r["stages_run"])
    t = (d / "time.txt").read_text().split() if (d / "time.txt").exists() else []
    return {"dir": str(d), "status": r["status"], "exact": ok, "stages": st, "position": r["position"],
            "token": r["token"], "binary_sha256": r["binary_sha256"], "result_sha256": sha(d / "result.json"),
            "x_checks": {k: v["mismatches"] for k, v in r["layer_x_checks"].items()},
            "kv_writeback_checks": r["token_kv_writeback_checks"], "max_rss_kib_wall_s": t[:2]}, log


def segments(log: str):
    """cycles per program segment from the per-cycle trace of a single-stage job (die 0 and die 3)."""
    m = re.search(r"STAGE \S+ done cycles=(\d+) start_cyc=(\d+) end_cyc=(\d+)", log)
    start, end = int(m.group(2)), int(m.group(3))
    samples = [(int(c), int(a), int(b)) for c, a, b in re.findall(r"progress tick=\d+ cyc=(\d+) pc_base=(\d+)/(\d+)", log)]
    seen = sorted({c for c, *_ in samples if start <= c < end})
    if len(seen) != end - start:
        raise SystemExit(f"trace has {len(seen)} of {end - start} cycles (RT_PROGRESS=1 required)")
    per = {}
    first = {}
    for c, a, b in samples:
        if start <= c < end:
            if a != b:
                raise SystemExit(f"dies 0 and 3 in different segments at cycle {c}")
            idx = max(i for i, base in enumerate(SEG_BASES) if base <= a)
            per[SEG_NAMES[idx]] = per.get(SEG_NAMES[idx], 0) + 1
            first.setdefault(SEG_NAMES[idx], c - start)
    return {"cycles": per, "first_cycle": first, "total": end - start}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=Path, required=True, help="runs/ with P<P>/L0 and P<P>/L0+L1+L2")
    ap.add_argument("--positions", default="255,4095,8191")
    ap.add_argument("--p255-summary", type=Path, required=True, help="results/rtl/qwen_rom_realmem_fulltoken_20261004/P255/summary.json")
    ap.add_argument("--gold-oracle", type=Path, required=True, help="the GPU golden oracle.json (3 layers)")
    ap.add_argument("--clock-ghz", type=float, default=1.2)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    p255 = json.loads(a.p255_summary.read_text())
    E, head = p255["per_layer_cycles"]["E"], p255["per_layer_cycles"]["head"]
    hz = a.clock_ghz * 1e9
    rows, trace = {}, {}
    for P in (int(x) for x in a.positions.split(",")):
        iso, log = job(a.runs / f"P{P}" / "L0")
        trace[P] = segments(log)
        ch = None
        if (a.runs / f"P{P}" / "L0+L1+L2" / "result.json").exists():
            ch, _ = job(a.runs / f"P{P}" / "L0+L1+L2")
        elif P == 255:  # the P255 record's chained E,L0,L1,L2
            c = p255["per_layer_cycles"]
            ch = {"exact": True, "stages": {"L0": {"cycles": c["chained_L0"]}, "L1": {"cycles": c["chained_L1"]},
                                            "L2": {"cycles": c["chained_L2"]}}, "dir": "P255 record (E+L0+L1+L2)"}
        l0 = iso["stages"]["L0"]["cycles"]
        steady = [ch["stages"][n]["cycles"] for n in ("L1", "L2")]
        mean, mx = sum(steady) / 2, max(steady)
        tok = 7 + E + (l0 - 1) + 35 * mean + (head - 1) + 37
        tok_max = 7 + E + (l0 - 1) + 35 * mx + (head - 1) + 37
        tok_iso = 7 + E + 36 * (l0 - 1) + (head - 1) + 37
        rows[P] = {"isolated_L0": l0, "isolated_exact": iso["exact"], "chained": {n: ch["stages"][n]["cycles"] for n in ("L0", "L1", "L2")},
                   "chained_exact": ch["exact"], "chained_steady_mean": mean, "chained_steady_max": mx,
                   "chained_penalty_vs_isolated": [s - (l0 - 1) for s in steady],
                   "token_cycles": round(tok), "token_cycles_max": tok_max, "token_cycles_isolated_lower_bound": tok_iso,
                   "token_us": round(tok / hz * 1e6, 2), "tok_per_s": round(hz / tok, 1), "tok_per_s_max": round(hz / tok_max, 1),
                   "isolated_job": iso, "chained_job": ch if "binary_sha256" in ch else {"source": ch["dir"]},
                   "segments_isolated_L0": trace[P]}
    ps = sorted(rows)
    # context-proportional cycles: least-squares slope of segment-0 cycles over P (only QK/softmax/PV scale with P)
    xs = ps
    ys = [trace[p]["cycles"]["attn_block_pc0_17"] for p in ps]
    n = len(xs)
    mx_, my_ = sum(xs) / n, sum(ys) / n
    slope = sum((x - mx_) * (y - my_) for x, y in zip(xs, ys)) / sum((x - mx_) ** 2 for x in xs)
    icpt = my_ - slope * mx_
    for p in ps:
        r = rows[p]
        seg = trace[p]["cycles"]
        r["attention"] = {
            "attn_block_cycles": seg["attn_block_pc0_17"], "mlp_block_cycles": seg.get("mlp_block_pc18_25"), "residual_cycles": seg.get("residual_pc26_28"),
            "attn_block_share_of_layer": round(seg["attn_block_pc0_17"] / trace[p]["total"], 4),
            "context_proportional_cycles": round(slope * p, 1),
            "context_proportional_share_of_layer": round(slope * p / trace[p]["total"], 4),
            "context_proportional_share_of_token": round(36 * slope * p / r["token_cycles"], 4)}
    gold = json.loads(a.gold_oracle.read_text())
    base = rows[255]
    res = {
        "schema": "opentallas.qwen-rom-realmem-context.v1",
        "configuration": p255["configuration"],
        "method": __doc__.split("\n\n", 1)[1].strip(),
        "golden": {"oracle_json_sha256": sha(a.gold_oracle), "layers": gold["layers"], "tokens_sha256": gold["tokens_sha256"],
                   "positions": gold["positions"], "tokens_at": {p: gold["per_position"][p]["token"] for p in gold["per_position"]},
                   "prompt": "the 4,118-token prompt of the P255 record followed by its first 4,074 tokens (8,192 tokens; positions "
                             "< P are golden sequential decode)",
                   "p255_crosscheck": "P255 L0..L2 X, kv_pre and kv_at_P sha256 equal to the committed 36-layer GPU golden (12/12 each)"},
        "E_cycles_from_P255": E, "head_cycles_from_P255": head,
        "attention_fit": {"segment0_cycles_vs_P_slope": round(slope, 5), "intercept": round(icpt, 1),
                          "points": dict(zip(ps, ys))},
        "per_position": rows,
        "vs_P255": {p: {"isolated_layer_ratio": round(rows[p]["isolated_L0"] / base["isolated_L0"], 3),
                        "chained_layer_ratio": round(rows[p]["chained_steady_mean"] / base["chained_steady_mean"], 3),
                        "token_ratio": round(rows[p]["token_cycles"] / base["token_cycles"], 3)} for p in ps},
        "model_reference": {
            "source": "docs/HEADLINE_BUNDLE_SCOPE.md / results/uarch/qwen_rom_calibrated_calendar_20261003/summary-r1.json",
            "context": "8K window, decode position 8,191, batch 1, AR, FP8 KV",
            "calibrated_finite_calendar": {"token_us": 357.99, "tok_per_s": 2793},
            "near_hbm_selected_for_build": {"token_us": 190.97, "tok_per_s": 5237},
            "uarch_model": {
                "source": "tools/uarch_model.py qwen_tp_point(4, 6144, 'board', ctx=...) (qwen_eval/qwen_tp_point default ctx=8192; "
                          "results/uarch/consolidation.json qwen_rom.product_row ctx 8192 = 9,367.6 tok/s)",
                "clock_hz": 1098640000.0,
                "per_ctx": {"256": {"cycles": 107917, "layer_chain_cycles": 2010, "tok_per_s": 10180.4},
                            "4096": {"cycles": 112237, "layer_chain_cycles": 2130, "tok_per_s": 9788.6},
                            "8192": {"cycles": 117281, "layer_chain_cycles": 2270, "tok_per_s": 9367.6}}}},
        "clock_ghz": a.clock_ghz,
        "claim_boundary": "Verilator RTL of the REAL_MEM TP4 runtime (one layer isolated + 3 chained per position), exact vs the GPU "
                          "ISA golden; the 36-layer token is composed (owner rule), not simulated whole. Clock assumed 1.2 GHz.",
    }
    if 8191 in rows:
        r = rows[8191]
        res["model_reference"]["measured_over_calibrated"] = round(r["tok_per_s"] / 2793, 3)
        res["model_reference"]["measured_over_near_hbm"] = round(r["tok_per_s"] / 5237, 3)
        res["model_reference"]["measured_over_uarch_model_8192"] = round(r["tok_per_s"] / 9367.6, 3)
        res["model_reference"]["measured_chained_layer_over_uarch_layer_chain_8192"] = round(r["chained_steady_mean"] / 2270, 3)
    if 4095 in rows:
        r = rows[4095]
        res["model_reference"]["measured_over_uarch_model_4096"] = round(r["tok_per_s"] / 9788.6, 3)
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({p: {k: rows[p][k] for k in ("isolated_L0", "chained", "chained_steady_mean", "token_cycles", "tok_per_s",
                                                  "tok_per_s_max", "isolated_exact", "chained_exact", "attention")} for p in ps}, indent=1))
    print(json.dumps({k: res[k] for k in ("vs_P255", "attention_fit")}, indent=1), json.dumps(res["model_reference"]))


if __name__ == "__main__":
    main()
