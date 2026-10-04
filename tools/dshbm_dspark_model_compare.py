#!/usr/bin/env python3
"""DSpark on the V4.1 HBM comparator: measured RTL cycles against the speculation price's model terms.

    python3 tools/dshbm_dspark_model_compare.py --composer COMPOSER.py --fullshape FULL.json --argmax ARGMAX.json \
        --bench BENCH.json [--bench ...] --out results/rtl/dshbm_dspark_rtl_20261003/model_compare.json

COMPOSER is the W19 composer the DSpark price used (claude/v41-hbm-speculation-20261003 @ d2aff19ef vendored it as
results/speculative/v41_hbm_speculation_methods_20261003/inputs/w19_hbm_token_compose_71b3ffc5.py; pass that file,
e.g. extracted with `git show d2aff19ef:<path>`).  Its SMTable over W19's measured SM records gives the line-rate price
the model used for the three DSpark SM shapes no RTL had run; its arch-DAG price of `argmax_local` is the model's
local argmax.  This tool sets the RTL measurements beside them:
  * SM element (rtl/gpu/ot_gpu_sm_v.sv, released weights, the busiest SM of a TP-96 die): the Markov head (one serial
    column), the LM head on the 5 block slots, main_proj -- model op time = (lines + drain) / 1.2 GHz;
  * the argmax epilogue (rtl/gpu/dshbm/ot_dshbm_argmax.sv): one SM's 43 Markov-biased logits and the die's 32-SM merge
    vs the model's argmax_local;
  * the control loop (ot_dshbm_dspark_ctl): its own cycles per step outside engine commands (the model has none).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F_FAST = 1.2e9


def load(p):
    return json.loads(Path(p).read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--composer", type=Path, required=True)
    ap.add_argument("--fullshape", type=Path, required=True)
    ap.add_argument("--argmax", type=Path, required=True)
    ap.add_argument("--bench", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("w19c", a.composer)
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
    sm = C.SMTable([load(ROOT / "results/rtl/w19_sm_real_ops.json"), load(ROOT / "results/rtl/w19_sm_real_ops_oreduce.json")],
                   "ar")
    full = load(a.fullshape)
    rows = []
    for c in full["cases"]:
        fmt = c["fmt"]
        lines, drain, how = sm.op(fmt, c["K"], c["sm_rows"])
        model_cyc = lines + drain
        meas = c["rtl"]["cycles_start_to_done"]
        rows.append(dict(case=c["case"], fmt=fmt, K=c["K"], sm_rows=c["sm_rows"], cols=c["cols"], exact=c["exact"],
                         model_how=how, model_lines=lines, model_drain=drain, model_cycles=model_cyc,
                         model_ns=round(model_cyc / F_FAST * 1e9, 1), rtl_cycles=meas,
                         rtl_ns=round(meas / F_FAST * 1e9, 1), rtl_lines=c["rtl"].get("lines"),
                         ratio_rtl_over_model=round(meas / model_cyc, 3)))
    am = load(a.argmax)["timing"]
    model_am_ns, dom = C.local_cycles(dict(fn="argmax_local"), {})
    rtl_am_cyc = am["sm_epilogue_43_bias"]["cycles_first_beat_to_result"] + am["sm_merge_32"]["cycles_first_beat_to_result"]
    argmax = dict(model_argmax_local_ns=round(model_am_ns, 1), model_domain=dom,
                  rtl_sm_epilogue_43_cycles=am["sm_epilogue_43_bias"]["cycles_first_beat_to_result"],
                  rtl_sm_merge_32_cycles=am["sm_merge_32"]["cycles_first_beat_to_result"],
                  rtl_total_cycles=rtl_am_cyc, rtl_total_ns=round(rtl_am_cyc / F_FAST * 1e9, 1),
                  rtl_die_single_stream_1347_cycles=am["die_stream_1347_bias"]["cycles_first_beat_to_result"],
                  note="the RTL figure is the per-SM epilogue (43 logits + the Markov bias add) then one more pass over "
                       "the 32 SM winners on the die; the cross-die 96-way merge is the collective the model prices "
                       "separately (topk_merge) and is not re-measured here")
    loops = []
    for b in a.bench:
        r = load(b)
        if r.get("mutation"):
            continue
        s = r["summary"]
        steps = max(1, s.get("steps", 0))
        ctl = s["cyc_total"] - s["cyc_engine"]
        loops.append(dict(trace=r["trace"]["drafter"], window=r["trace"]["window"], steps=s["steps"],
                          cyc_total=s["cyc_total"], cyc_engine=s["cyc_engine"], cyc_control=ctl,
                          note="cyc_control covers prefill + steps; engine cycles here are the replayed bench's, not "
                               "the SM cluster's"))
    mk = next(r for r in rows if r["case"] == "markov_head")
    markov_step = dict(rtl_sm_markov_head_ns=mk["rtl_ns"], model_sm_markov_head_ns=mk["model_ns"],
                       rtl_argmax_ns=argmax["rtl_total_ns"], model_argmax_ns=argmax["model_argmax_local_ns"],
                       delta_ns_per_step=round((mk["rtl_ns"] - mk["model_ns"]) + (argmax["rtl_total_ns"] -
                                                                                 argmax["model_argmax_local_ns"]), 1))
    markov_step["delta_us_per_draft_5_steps"] = round(5 * markov_step["delta_ns_per_step"] / 1e3, 3)
    out = dict(schema="opentallas.rtl.dshbm_dspark_model_compare.v1",
               composer=dict(path=str(a.composer), sha256=hashlib.sha256(a.composer.read_bytes()).hexdigest(),
                             origin="claude/v41-hbm-speculation-20261003 @ d2aff19ef, inputs/w19_hbm_token_compose_71b3ffc5.py"),
               sm_shapes=rows, argmax=argmax, markov_step=markov_step, control_loop=loops,
               model_draft_us=dict(total=51.88, stages=41.19, head=3.39, markov_step=1.46, markov_steps=5,
                                   source="v41_hbm_speculation_methods.json draft.measured_union (d2aff19ef)"),
               inputs={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest()
                       for p in [a.fullshape, a.argmax] + list(a.bench)})
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(sm_shapes=[{k: r[k] for k in ("case", "model_how", "model_cycles", "rtl_cycles", "ratio_rtl_over_model")}
                                     for r in rows], argmax=argmax, markov_step=markov_step), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
