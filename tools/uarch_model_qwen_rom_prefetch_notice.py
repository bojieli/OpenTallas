#!/usr/bin/env python3
"""Qwen3-8B ROM near-HBM calendar with the next-layer KV prefetch NOTICE handshake.  Model only.

The streaming HBM3E controller (rtl/model_ready_hbm_r14/ot_hbm_r14_stream_*.sv, record
results/uarch/qwen_hbm_sustained_bw_20261003) sustains 0.958 TB/s per stack on the worst layer ONLY if its layer
descriptor is posted HINT controller cycles before the attention engine's `go` (stream-aware REFpb protects the sets
it needs first and opens their rows).  This tool composes that handshake into the near-HBM calendar of
results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json:

  NOTICE   the sequencer posts layer L+1's descriptor (layer row, sector count -- both known before the layer's q
           exists) the moment layer L's stream has ended; layer 0's descriptor is posted at the token start.
  LEAD     available notice lead = time from posting to the layer's attention `go`:
             layer 0:   QKV prefix of layer 0 (451 stream cycles; embedding hand-off not counted: conservative)
             layer L>0: the rest of layer L-1 after its stream (drain + return/hub + o-proj, AR, MLP, AR) plus the
                        QKV prefix of layer L = per_layer - (q_in + stream)
           converted to controller cycles (CK/2 = 976.6 MHz, 1.024 ns) and compared with the HINT the measured case
           needs.
  STREAM   the attention term is rebuilt from the measured worst layer: q_in + stream + drain + return_hub, where
           stream = the measured worst K+V layer time (first data included) at the stream clock, plus the
           HBM-service-clock -> engine-clock crossing (an asynchronous FIFO: the clocks do not share a PLL; 2-flop
           pointer synchroniser + read register = 3 engine cycles, once per layer on the first sector; the FIFO is
           sized at the service rate, so it never throttles the 0.98 TB/s data phase).
  CASES    the six measured controller groups (REFpb hint 320/200/100/0, back-to-back without notice, REFab hint 320)
           and the pricing's 0.9 TB/s analytical case for reference.

The K->V turnaround (max exchange, exp lead) is taken as hidden behind the landing buffer, as in the pricing record;
the body, all-reduces and non-layer cycles are the calendar's, unchanged.

    python3 tools/uarch_model_qwen_rom_prefetch_notice.py --result results/uarch/qwen_rom_prefetch_notice_20261003/model-r1.json
"""
import argparse
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json"
BW = ROOT / "results/uarch/qwen_hbm_sustained_bw_20261003/rtl-bench-r6.json"
STREAM_PS = F(2500, 3)          # 1.2 GHz
CTRL_PS = F(1024)               # HBM CK/2
NL = 36
PREFIX = 451                    # QKV prefix before attention (stream cycles; calendar PREFIX_CYCLES)
CDC_CYCLES = 3                  # async FIFO first-sector latency (engine cycles)
GROUP_HINT = {"REFpb_aware_hint320 (primary)": 320, "REFpb_aware_hint200": 200, "REFpb_aware_hint100": 100,
              "REFpb_aware_hint0": 0, "REFpb_aware_back_to_back": 0, "REFab_staggered_hint320": 320}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ceil(x):
    return int(-(-x // 1))


def compose(cal, stream_cycles, hint_ctrl):
    t = cal["composition"]["attention_terms_primary"]
    body, nonlayer = cal["composition"]["body_cycles"], cal["composition"]["nonlayer_cycles"]
    ar = (cal["headline"]["per_layer_cycles"] - body - t["total"]) // 2          # 991 measured
    att = t["q_in"] + stream_cycles + CDC_CYCLES + t["drain"] + t["return_and_hub"]
    per_layer = body + 2 * ar + att
    token = NL * per_layer + nonlayer
    lead0 = PREFIX
    leadL = per_layer - (t["q_in"] + stream_cycles + CDC_CYCLES)
    need_stream = ceil(F(hint_ctrl) * CTRL_PS / STREAM_PS)
    ok0, okL = lead0 >= need_stream, leadL >= need_stream
    t_s = token * STREAM_PS / F(10**12)
    return dict(attention_cycles=att, per_layer_cycles=per_layer, token_cycles=token, token_us=round(float(t_s) * 1e6, 3),
                tokens_per_s=round(1 / float(t_s), 1), allreduce_cycles=ar,
                notice=dict(hint_needed_ctrl_cycles=hint_ctrl, hint_needed_stream_cycles=need_stream,
                            lead_layer0_stream_cycles=lead0, lead_layerL_stream_cycles=leadL,
                            slack_layer0=lead0 - need_stream, slack_layerL=leadL - need_stream,
                            met_every_layer=ok0 and okL, exposed_cycles_per_token=max(0, need_stream - lead0)
                            + (NL - 1) * max(0, need_stream - leadL)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--result", type=Path, required=True)
    a = ap.parse_args()
    cal = json.loads(CAL.read_text())
    bw = json.loads(BW.read_text())
    cases = {}
    for g, hint in GROUP_HINT.items():
        rec = bw["groups"][g]
        stream = ceil(F(str(rec["worst_layer_stream_ns"])) * 1000 / STREAM_PS)
        c = compose(cal, stream, hint)
        c.update(source_group=g, measured_worst_layer_stream_ns=rec["worst_layer_stream_ns"],
                 measured_worst_layer_TBps=round(rec["worst_layer_Bps"] / 1e12, 3), stream_cycles=stream)
        if c["notice"]["exposed_cycles_per_token"]:
            c["token_cycles"] += c["notice"]["exposed_cycles_per_token"]
            ts = c["token_cycles"] * STREAM_PS / F(10**12)
            c["token_us"], c["tokens_per_s"] = round(float(ts) * 1e6, 3), round(1 / float(ts), 1)
        cases[g] = c
    t = cal["composition"]["attention_terms_primary"]
    ref = compose(cal, t["K_phase"] + t["V_phase"], 0)
    ref["note"] = "the calendar's analytical 0.9 TB/s stream (K 700 + V 700) plus the crossing term; no notice needed"
    prim = cases["REFpb_aware_hint320 (primary)"]
    out = dict(
        schema="qrom-near-hbm-prefetch-notice-calendar.v1", status="MODEL_ONLY",
        inputs={str(CAL.relative_to(ROOT)): sha(CAL), str(BW.relative_to(ROOT)): sha(BW), "tool": sha(__file__)},
        handshake=("sequencer posts layer L+1's KV descriptor at the end of layer L's stream (layer 0: at token start); "
                   "descriptor = layer row + sector count, independent of q; controller go = attention start"),
        constants=dict(stream_clock_ps=str(STREAM_PS), controller_clock_ps=str(CTRL_PS), layers=NL, qkv_prefix=PREFIX,
                       cdc_first_sector_cycles=CDC_CYCLES),
        calendar_reference_0p9TBps=ref, cases=cases,
        headline=dict(case="REFpb stream-aware, notice 320 controller cycles (measured worst layer 0.958 TB/s)",
                      token_cycles=prim["token_cycles"], token_us=prim["token_us"], tokens_per_s=prim["tokens_per_s"],
                      notice_met_every_layer=prim["notice"]["met_every_layer"],
                      layer0_slack_stream_cycles=prim["notice"]["slack_layer0"],
                      vs_calendar_0p9=round(prim["tokens_per_s"] / cal["headline"]["tokens_per_s"] - 1, 4)),
        caveats=["body/AR/non-layer cycles are the calendar's (position-0 measured body, AR 991 two-segment)",
                 "K->V turnaround hidden behind the landing buffer (pricing assumption, not measured)",
                 "layer-0 lead counts only the QKV prefix (embedding hand-off excluded)",
                 "the KV write path (new token's K/V to the owner stack) is not in the streaming controller"])
    a.result.parent.mkdir(parents=True, exist_ok=True)
    with a.result.open("x") as f:
        f.write(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["headline"], indent=1))
    for k, c in cases.items():
        print(f"{k:34s} stream {c['stream_cycles']:5d}  token {c['token_cycles']}  {c['tokens_per_s']} tok/s  "
              f"notice met {c['notice']['met_every_layer']}  slack L0 {c['notice']['slack_layer0']} L {c['notice']['slack_layerL']}")


if __name__ == "__main__":
    main()
