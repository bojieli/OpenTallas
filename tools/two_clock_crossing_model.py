#!/usr/bin/env python3
"""Model of the 3:4 related-clock crossing ot_ratio_cdc_fifo (rtl/common/ot_ratio_cdc_fifo.sv), priced into the token.

Model first (AGENTS.md design method): this tool states, before any RTL measurement is trusted,
  * the latency of one word in each direction for every phase of the 12-tick (3.333 ns) VCO pattern,
    accept edge -> consumer accept edge, with no backpressure;
  * the saturated throughput per DEPTH, from a tick-level event model of the pointer protocol;
  * the token price: tools/uarch_model.py charges every cross-domain dependency edge CDC_W18 =
    4 slow cycles (fast->slow) / 5 fast cycles (slow->fast).  The tool re-prices the V4.1 ROM clock-domain case (b)
    and the W10 baseline with the successor's worst-case latency, by patching CDC_W18 in-process only
    (tools/uarch_model.py is not edited).  The Qwen3-8B ROM model has no split-clock term (all 1.2 GHz), so the
    Qwen price is the RTL-measured cycle delta of the integration bench, not a model number.

    python3 tools/two_clock_crossing_model.py --output R.json [--no-price]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TICK_PS = Fraction(2500, 9)            # one 3.6 GHz VCO period
FAST, SLOW = 3, 4                      # ticks per cycle
PATTERN = 12                           # lcm(3, 4)


def next_edge_after(t: int, per: int, off: int = 0) -> int:
    """First edge of a clock (period per, phase off) strictly after tick t (a coincident edge samples old values)."""
    k = (t - off) // per + 1
    return off + k * per


def schedule_transfers(release_ticks, *, wper, rper, depth=4,
                       reader_busy_cycles=1, reader_blocked_ticks=()):
    """Finite-credit calendar for the existing related-clock FIFO, once live.

    Input words are held in their original order from release until acceptance.
    Ticks use the existing 3.6-GHz grid; coincident edges sample OLD peer state.
    A word retires only on reader acceptance, not pointer/shadow capture. Both
    data storage and returned credits are finite. This API lets a parent model
    compose actual command/data/status dependencies without substituting a
    constant CDC surcharge or pricing delayed publication as immediate.

    Payload widths, bank service, reset recovery and the enclosing instruction
    schedule remain the parent's explicit costs. This is not token timing or a
    replacement for the selected W12 tag/valid enrollment.
    """
    release = list(release_ticks)
    blocked = set(reader_blocked_ticks)
    if (wper, rper) not in ((FAST, SLOW), (SLOW, FAST)):
        raise ValueError("clock periods must be the existing related 3:4 pair")
    if depth < 2 or depth & (depth - 1) or reader_busy_cycles < 1:
        raise ValueError("power-of-two depth >=2 and positive reader service required")
    if any(type(t) is not int or t < 0 for t in release + list(blocked)):
        raise ValueError("release and blocked times must be nonnegative integer ticks")
    if release != sorted(release):
        raise ValueError("producer release order must be preserved")
    wp = rp = wp_r = rp_w = 0
    last_wp = last_rp = 0
    next_reader = 0
    rows = []
    tick = 0
    while rp < len(release):
        we, re = tick % wper == 0, tick % rper == 0
        # last_* deliberately excludes writes/retirements at this same edge.
        if we:
            if wp < len(release) and release[wp] <= tick and wp - rp_w < depth:
                rows.append(dict(word=wp, release_tick=release[wp],
                                 accepted_tick=tick))
                wp += 1
            rp_w = last_rp
        if re:
            if (wp_r != rp and tick >= next_reader and tick not in blocked):
                rows[rp]["retired_tick"] = tick
                rows[rp]["credit_wait_ticks"] = rows[rp]["accepted_tick"] - release[rp]
                rows[rp]["crossing_and_reader_wait_ticks"] = tick - rows[rp]["accepted_tick"]
                rp += 1
                next_reader = tick + reader_busy_cycles * rper
            wp_r = last_wp
        # At the next event edge this tick's publications become visible.
        last_wp, last_rp = wp, rp
        tick = min(next_edge_after(tick, wper), next_edge_after(tick, rper))
    return rows


def latency_table(wper: int, rper: int) -> list[dict]:
    """Accept edge t_w (writer) -> the reader's accept edge.  The entry, its write pointer and the writer state are
    launched at t_w; the first reader edge strictly after t_w captures them into the shadow/pointer samplers, r_v
    rises after that edge, and the consumer accepts at the next reader edge."""
    rows = []
    for tw in range(0, PATTERN, wper):
        cap = next_edge_after(tw, rper)
        acc = cap + rper
        rows.append(dict(write_tick=tw, capture_ticks=cap - tw, consumer_accept_ticks=acc - tw,
                         consumer_accept_dst_cycles=str(Fraction(acc - tw, rper)),
                         consumer_accept_ps=round(float((acc - tw) * TICK_PS), 1)))
    return rows


def throughput(wper: int, rper: int, depth: int, ticks: int = 120000) -> float:
    """Tick-level event model of the pointer protocol, writer always valid, reader always ready.
    Writer: w_rdy = (wp - rp_w) != depth on registered values; reader: r_v = (wp_r != rp).
    Samplers capture the other side's register value as of the latest edge strictly before."""
    wp = rp = 0
    rp_w = wp_r = 0
    hist_wp, hist_rp = {}, {}             # register value after each edge tick
    last_w = last_r = None
    takes = []
    for t in range(ticks):
        we, re_ = t % wper == 0, t % rper == 0
        if not (we or re_):
            continue
        # values the other side's samplers see at this edge: the peer register as of the latest peer edge < t
        wp_seen = hist_wp.get(last_w, 0) if last_w is not None else 0
        rp_seen = hist_rp.get(last_r, 0) if last_r is not None else 0
        nwp, nrp, nrp_w, nwp_r = wp, rp, rp_w, wp_r
        if we:
            if (wp - rp_w) != depth:
                nwp = wp + 1
            nrp_w = rp_seen
        if re_:
            if wp_r != rp:
                nrp = rp + 1
                takes.append(t)
            nwp_r = wp_seen
        wp, rp, rp_w, wp_r = nwp, nrp, nrp_w, nwp_r
        if we:
            hist_wp[t] = wp
            last_w = t
        if re_:
            hist_rp[t] = rp
            last_r = t
    span = (takes[-1] - takes[len(takes) // 2]) * TICK_PS / 1000
    return round((len(takes) - 1 - len(takes) // 2) / float(span), 4)


def summarise(rows, rper):
    v = [r["consumer_accept_ticks"] for r in rows]
    return dict(min_ticks=min(v), max_ticks=max(v), mean_ticks=str(Fraction(sum(v), len(v))),
                min_dst_cycles=str(Fraction(min(v), rper)), max_dst_cycles=str(Fraction(max(v), rper)),
                mean_dst_cycles=round(sum(v) / len(v) / rper, 4),
                max_ps=round(float(max(v) * TICK_PS), 1), mean_ps=round(float(Fraction(sum(v), len(v)) * TICK_PS), 1))


def price(f2s_slow_cycles: float, s2f_fast_cycles: float) -> dict:
    sys.path.insert(0, str(ROOT / "tools"))
    import uarch_model as U  # noqa: E402
    S = U.cons_min_stages("analytical", U.CONS["overhead"], "ring", U.PRODUCT_GEOM, U.PRODUCT_PITCH, "columns", "4096m8")
    h = U.cons_head_dies("analytical", U.CONS["overhead"], "ring", U.PRODUCT_GEOM, U.PRODUCT_PITCH, "8192m8")
    t = U.cons_table_dies("analytical", U.CONS["overhead"])["dies"]
    keep = dict(U.CDC_W18)
    out = {}
    for tag, f2s, s2f in (("charged_W18_4_slow_5_fast", keep["fast_to_slow_slow_cycles"], keep["slow_to_fast_fast_cycles"]),
                          ("successor_worst_case", f2s_slow_cycles, s2f_fast_cycles),
                          ("zero_cdc_bound", 0, 0)):
        U.CDC_W18.update(fast_to_slow_slow_cycles=f2s, slow_to_fast_fast_cycles=s2f)
        cases = U.cons_clock_cases(S, h, t)
        b = cases["b: 1.2 GHz field (LAT 7) + 0.9 GHz chain units (LAT 3), W18 CDC"]
        w10 = U.w10_baseline_model()
        out[tag] = dict(cdc_fast_to_slow_slow_cycles=f2s, cdc_slow_to_fast_fast_cycles=s2f,
                        v41_case_b_ar_tokens_s_b1=b["ar_tokens_s_b1"], v41_case_b_mtp_tokens_s_b1=b["mtp_tokens_s_b1"],
                        w10_baseline=_w10_rows(w10))
    U.CDC_W18.clear()
    U.CDC_W18.update(keep)
    base = out["charged_W18_4_slow_5_fast"]["v41_case_b_ar_tokens_s_b1"]
    succ = out["successor_worst_case"]["v41_case_b_ar_tokens_s_b1"]
    out["v41_case_b_gain_successor_vs_charged"] = round(succ / base - 1, 5)
    out["inputs"] = dict(stages=S, head_dies=h, table_dies=t, uarch_model_sha256=_sha(ROOT / "tools/uarch_model.py"))
    out["qwen3_rom"] = ("tools/uarch_model.py prices Qwen3-8B ROM all at 1.2 GHz (PRODUCT_CLOCK_HZ, QWEN_SS: no slow "
                        "domain, no CDC term); its split-clock cost is the RTL-measured cycle delta of the integration "
                        "bench (results/rtl/two_clock_crossing_20261003), not a model figure")
    return out


def _w10_rows(w10):
    c = w10["composition"]
    return {k: c[k]["ar_tokens_s"] for k in ("product_unchanged_lat7", "checked_in_lat8_audit")}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--no-price", action="store_true")
    a = ap.parse_args(argv)
    f2s, s2f = latency_table(FAST, SLOW), latency_table(SLOW, FAST)
    rec = dict(schema="opentallas.two_clock_crossing_model.v1",
               rtl="rtl/common/ot_ratio_cdc_fifo.sv", rtl_sha256=_sha(ROOT / "rtl/common/ot_ratio_cdc_fifo.sv"),
               tool_sha256=_sha(Path(__file__)),
               clocking=dict(vco_ghz=3.6, tick_ps=str(TICK_PS), fast_ticks=FAST, slow_ticks=SLOW, related=True,
                             basis="one PLL per die, /3 and /4 of one VCO (results/physical_abi3/asap7/chip/v41_w18/"
                                   "clock_plan.json; AGENTS.md clock domains); gcd(3,4)=1 so every divider phase gives "
                                   "the same edge-spacing set {0..4} ticks: setup window 1 tick, hold at coincidence"),
               latency=dict(definition="writer accept edge -> consumer accept edge, consumer always ready, one word in "
                                       "flight (a same-clock registered FIFO stage is 1 destination cycle)",
                            fast_to_slow=dict(per_phase=f2s, **summarise(f2s, SLOW)),
                            slow_to_fast=dict(per_phase=s2f, **summarise(s2f, FAST)),
                            model_charge=dict(fast_to_slow_slow_cycles=4, slow_to_fast_fast_cycles=5,
                                              src="tools/uarch_model.py CDC_W18"),
                            predecessor_measured=dict(fast_to_slow_slow_cycles="3.00/3.38/3.75 sparse, 15.01 max stalled",
                                                      slow_to_fast_fast_cycles="3.67/4.00/4.34 sparse, 9.01 max stalled",
                                                      src="results/uarch/dsrom_ratio_fifo_gap_20261003/model.json")),
               throughput_words_per_ns={f"DEPTH{d}": dict(fast_to_slow=throughput(FAST, SLOW, d),
                                                          slow_to_fast=throughput(SLOW, FAST, d)) for d in (2, 4, 8)},
               throughput_ceiling_words_per_ns=0.9)
    if not a.no_price:
        rec["token_price"] = price(float(Fraction(rec["latency"]["fast_to_slow"]["max_dst_cycles"])),
                                   float(Fraction(rec["latency"]["slow_to_fast"]["max_dst_cycles"])))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(f2s=rec["latency"]["fast_to_slow"]["max_dst_cycles"],
                          s2f=rec["latency"]["slow_to_fast"]["max_dst_cycles"],
                          thr=rec["throughput_words_per_ns"],
                          price={k: v for k, v in rec.get("token_price", {}).items() if k != "inputs"}), indent=1))


if __name__ == "__main__":
    main()
