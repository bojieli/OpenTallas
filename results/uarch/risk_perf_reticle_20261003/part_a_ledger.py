#!/usr/bin/env python3
"""Part A: measured-vs-model performance ledger against the written targets (model-only composition).

Every input is a literal copied from a named, source-pinned record (see SOURCES); nothing is
re-simulated.  Each combination is composed three ways:
  central = best estimate (measured terms + model terms as recorded + measured improvements),
  low     = every unmeasured term and pending penalty at its adverse bound,
  high    = favourable bound (measured improvements fully realised).
Run: python3 part_a_ledger.py > part_a_ledger.json
"""
import json

F_STREAM = 1.2e9          # AGENTS.md:33 streaming clock target
F_LOW = 1.0e9             # clock-ceiling risk case requested by the owner (1.0 GHz)

SOURCES = {
    "qwen_layer_parallel": "claude/layer-parallel-sim-20261003 @ 4c51918c9 results/rtl/qwen_rom_TP4_allreduce_oneseg_fulltoken_20261003/{REPLAY.md,verdict.json}",
    "qwen_nearhbm_attn": "claude/qwen-nearhbm-attn-20261003 @ ba283a6ad results/uarch/qwen_nearhbm_attn_rtl_20261003/REPLAY.md (cycles table)",
    "qwen_hbm_bw": "claude/qwen-hbm-sustained-bw-20261003 @ 52ce3e9c1 results/uarch/qwen_hbm_sustained_bw_20261003/README.md",
    "qwen_calibrated": "main results/uarch/qwen_rom_calibrated_calendar_20261003/{baseline-r1,near-hbm-selected-r1,summary-r1}.json",
    "qwen_dspark": "claude/qwen-rom-speculation-recheck-20261003 @ f10a0df32 results/speculative/qwen_rom_speculation_recheck_20261003/pricing.json results.dspark.m1_widenedAR_attn2_overlap",
    "qwen_hbm": "main results/uarch/hbm_gpu.json rows[design=qwen_hbm_gpu], speculation[qwen_hbm_dflash_b16]",
    "ds_rom_c1": "claude/dsrom-c5hc-adopt-20261003 @ 4ec2eef0e results/rtl/dsrom_c5hc_collective_gate_20261003/REPLAY.md",
    "ds_free_levers": "claude/free-levers-audit-20261003 @ b98b05222 results/uarch/free_levers_audit_20261003/free_levers_audit.md",
    "ds_qpipe": "claude/dsrom-qelem-pipeline-20261003 @ 0b831a7d4 results/uarch/dsrom_qelem_pipeline_pricing_20261003.json",
    "ds_qtiming_fail": "claude/dsrom-qelem-timing-20261003 @ 693a69076 (post-CTS -316/-437 ps, zero-latency fixes FAIL)",
    "two_clock": "claude/two-clock-rtl-20261003 @ 27d86cfe results/rtl/two_clock_crossing_20261003/REPLAY.md",
    "ds_hbm_spec": "claude/v41-hbm-speculation-20261003 @ d2aff19ef results/speculative/v41_hbm_speculation_methods_20261003/REPLAY.md",
    "ds_hbm_ar": "main results/uarch/consolidation.json headline_table.v41[1] (HBM_W19 fused 442.14 us)",
    "ds_mtp_budget": "main results/uarch/ds_mtp_headline_budget_20261002/model.json",
}

TARGETS = {
    "qwen_rom": [
        {"value_tok_s": 3000, "kind": "current conditional target, AR, 8K, batch 1 (TP-4 option C)",
         "where": ["results/uarch/qwen_rom_calibrated_calendar_20261003/baseline-r1.json:873 bounds.target_3k_s",
                   "results/uarch/qwen_rom_kv_successor_20261002/model-r7.json:66 dimensioning.target_s",
                   "docs/MICROARCH_MODEL.md:132", "docs/HEADLINE_BUNDLE_SCOPE.md:77"]},
        {"value_tok_s": 11325, "kind": "historical TP-2 budget target (superseded design, docs/ARCH_SPEC_QWEN3.md:3)",
         "where": ["docs/ARCH_SPEC_QWEN3.md:90,95"]},
    ],
    "qwen_hbm": [{"value_tok_s": None, "kind": "NOT WRITTEN: comparator, no absolute or ratio target found"}],
    "ds_rom": [
        {"value_tok_s": 3000, "kind": "owner target: >3,000 ACCEPTED tok/s after MTP (AR reported separately), 1M",
         "where": ["TASKS.md:245", "TASKS.md:46", "TASKS.md:91", "docs/CURRENT_WORK_HANDOFF_2026_10_03.md:24",
                   "results/uarch/ds_mtp_headline_budget_20261002/model.json:39 target_committed_tokens_per_second"]},
        {"value_tok_s": 4599, "kind": "spec requirement AR at 1M (4,837 at 200K)", "where": ["docs/ARCH_SPEC_V41.md:21-22,44"]},
        {"value_tok_s": 9500, "kind": "spec budgeted design with DSpark MTP at 1M (tau 3.65)", "where": ["docs/ARCH_SPEC_V41.md:23,575"]},
    ],
    "ds_hbm": [{"value_tok_s": None, "kind": "NOT WRITTEN: comparator; ARCH_SPEC_V41.md:24 records a budget RESULT (926 AR / 1,221 MTP equal-area), not a target"}],
    "ratios": "NOT WRITTEN: no ROM/HBM ratio target exists in AGENTS.md, INTEGRATED_PHYSICAL_PLAN.md, TASKS.md, HEADLINE_BUNDLE_SCOPE.md, the handoff or ARCH_SPEC_*; Atlas ratios (12.3x Qwen, DS 7,049 comparisons) are historical results.",
}


def rate(us):
    return 1e6 / us


# ---------------- Qwen3-8B ROM (TP-4 option C, 8K, pos 8191, AR) ----------------
def qwen_rom():
    layer_meas = 3930          # measured chained layer, one-stream AR, pos 0 (4c51918c9)
    pos0_attn = 87             # pos-0 attention trace span inside the layer (baseline-r1 compute.measured)
    head = 2998                # measured head, chained
    layers = 36
    body_ar = layer_meas - pos0_attn          # 3,843 = body + 2 one-stream all-reduces (measured)
    attn = {"central": 1824,   # R=8 RTL, final SS-pipelined exp/recip, HBM model 0.9 TB/s (ba283a6ad)
            # high: measured 0.958 TB/s worst layer (798 B/edge) shortens K (739) and HBM-bound V (801) by ~6%,
            #       less 2x14 cycles of measured go->first-data (24.6 ns vs 16-cycle bench latency)
            "high": 1824 - round(739 * (1 - 750 / 798)) - round(801 * (1 - 750 / 798)) + 28,
            # low: R=6 (2,022, the area-priced instance) if R=8 area does not fit + first-data 28 + async CDC 2x4
            "low": 2022 + 28 + 8}
    # per layer, LOW only: the corridor gate's routed spans all miss SS setup by 11-58 ps at 504 um/stage, so the
    # reach shrinks to ~453 um (58 ps / 1.135 ps/um) and stage counts grow ~11%: +5 stages x 4 hub<->stack traversals
    # in attention + 11% of the 167 wire/arith extra cycles on each of ~4 serial ME ops = ~92 cycles
    wire_low = 92
    out = {}
    for case in ("central", "high", "low"):
        per_layer = body_ar + attn[case] + (wire_low if case == "low" else 0)
        cyc = layers * per_layer + head
        f = F_LOW if case == "low" else F_STREAM
        us = cyc / f * 1e6
        out[case] = dict(per_layer_cycles=per_layer, token_cycles=cyc, clock_hz=f, token_us=round(us, 3),
                         tok_s=round(rate(us), 1))
    out["terms"] = [
        {"term": "body + 2 one-stream all-reduces", "cycles_per_layer": body_ar, "class": "MEASURED (RTL, pos 0, bit-exact)"},
        {"term": "head", "cycles": head, "class": "MEASURED (RTL)"},
        {"term": "near-HBM attention ctx 8192", "cycles_per_layer": attn, "class": "MEASURED RTL cycles with MODELLED HBM (0.9 TB/s, 16-cycle latency); HBM rate itself MEASURED 0.958 TB/s on the streaming controller bench"},
        {"term": "HBM descriptor notice 261 cycles + REFpb", "class": "REQUIRED handshake, not yet in the attention RTL; 0.958 holds only with it (hint 200 -> 0.910, none -> 0.774)"},
        {"term": "clock", "class": "MODEL: 1.2 GHz assumed; near-HBM exp/recip close pre-layout only; BF16 MAC pipe closed at 1,040 MHz; HBM stream ctl closes at CK/2 (976.6 MHz), misses 1.2 GHz by 4.7 ps"},
        {"term": "wire stages hub<->shoreline and tile column", "class": "MODEL: 45 / 62 stages at 504 um/stage; corridor-gate routed spans miss SS by 11-58 ps (reach ~453 um), LOW adds +92 cycles/layer"},
        {"term": "embedding hand-off, owner-stack KV write, control share 5%, repeaters/CTS/PG", "class": "UNPRICED (near-hbm-selected-r1 unqualified_inputs)"},
    ]
    # fallback: no near-HBM attention.  The calibrated calendar is KV-fill-service bound (binder), so the
    # measured one-stream AR saving does not move it (baseline-r1 bounds: fill floor 281.4 us, command bus 308.2 us).
    out["fallback_without_near_hbm"] = dict(token_us=357.99, tok_s=2793.4, best_case_command_bus_floor_tok_s=round(rate(308.16), 1),
                                           note="baseline-r1.json bounds.binder = KV fill service; meets_3k=false")
    sp_c, sp_lo, sp_hi = 1.428, 1.249, 1.7966   # DSpark b4, 2x attention, widened AR, SU overlap (pricing.json)
    out["dspark_sensitivity"] = dict(
        central=round(out["central"]["tok_s"] * sp_c, 0), low=round(out["low"]["tok_s"] * sp_lo, 0),
        high=round(out["high"]["tok_s"] * sp_hi, 0), area_mm2_per_die=46.24,
        note="NOT the target mode (owner: Qwen ROM AR only); speedup from recheck pricing on its own AR basis (5,923), tau DERIVED from a paper ratio, no verify layer in RTL; +46 mm2/die only fits r2 at the r2 macro count")
    return out


# ---------------- Qwen3-8B HBM comparator (GPU-organised, 8K) ----------------
def qwen_hbm():
    ar = 880.5   # bandwidth-bound at 0.9 TB/s/stack (3,276.8 B/cycle at 1.0986 GHz, 4 stacks/die)
    out = {"central": dict(tok_s=ar, note="model basis 0.9 TB/s/stack; measured streaming 0.958 shows it is attainable"),
           "high": dict(tok_s=round(ar * 0.958 / 0.9, 1), note="weight stream at the measured 0.958 TB/s (needs a streaming REFpb controller, which a GPU has)"),
           "low": dict(tok_s=round(ar * 0.84 / 0.9, 1), note="0.84 TB/s: existing per-PC REFpb model worst layer (v41x_idx_hbm REFPB=3)"),
           "dflash_b16": dict(tok_s=2671, tau=3.656, note="hbm_gpu.json speculation; DFlash allowed on HBM comparators")}
    out["terms"] = [{"term": "HBM weight+KV stream", "class": "MODEL at 0.9 TB/s/stack; MEASURED feasibility 0.958 (ROM-side controller bench)"},
                    {"term": "SM barrier / drain", "class": "MEASURED RTL (48/89 cycles), hidden under the stream"},
                    {"term": "owner/ACK/CDC completion bridge, full connected RTL", "class": "UNPRICED / open (G2-G4)"}]
    return out


# ---------------- DeepSeek-V4.1 ROM array (S58 PAR2 = C1, 1M, batch 1) ----------------
def ds_rom():
    ar_us = rate(2356.8)                    # C1 with RTL-measured collectives (4ec2eef0e)
    mtp_step = 3.649 / 3203.4 * 1e6         # C1 MTP re-price, tau 3.649, draft 3/40 AR (assumed)
    draft_fix = (0.117 - 0.075) * ar_us     # real DSpark draft ratio measured on HBM composer (d2aff19ef)
    qpipe_ar, qpipe_mtp = 0.00086, 0.00045  # L=2 q-element pipelining (pricing record)
    recur_ar, recur_mtp = 0.00648, 0.01656  # one added cycle in the chunk-8 recurrence (pricing record)
    cdc_credit = 0.0060                     # ratio FIFO successor 2/2 vs charged 4/5: +0.54..0.65% (two-clock record)
    phase_merge_us = 87800 / F_STREAM * 1e6  # 320 phases x ~274 cycles not yet merged by the emitter (b98b05222)
    other_gaps_us = {"experts_gu one pass (#6)": 52000 / F_STREAM * 1e6,
                     "cross-unit chaining (#4)": 40000 / F_STREAM * 1e6,
                     "SU _kr fusion (#2)": 21700 / F_STREAM * 1e6}
    # clock ceiling: field (116 us) and kv (21.5 us) at 1.0/1.2, serial chain (162 us) at 0.75/0.9
    clock_ar_us = (116.0 + 21.5) * (1.2 / 1.0 - 1) + 162.0 * (0.9 / 0.75 - 1)
    clock_frac = clock_ar_us / ar_us
    taus = {"central_pinned_pooled": 3.649, "low_LMSYS_poetry": 2.91, "high_pilot_agentic_median": 4.69,
            "pilot_multiturn": 3.92, "LMSYS_GSM8K": 5.24, "chat_walk": 2.458}

    c_ar = ar_us * (1 + qpipe_ar - cdc_credit)
    c_step = (mtp_step + draft_fix) * (1 + qpipe_mtp - cdc_credit)
    l_ar = ar_us * (1 + qpipe_ar + recur_ar + clock_frac) + phase_merge_us
    l_step = (mtp_step + draft_fix) * (1 + qpipe_mtp + recur_mtp + clock_frac) + phase_merge_us
    h_ar = ar_us * (1 - cdc_credit)
    h_step = (mtp_step + draft_fix) * (1 - cdc_credit)
    floor_ar = l_ar + sum(other_gaps_us.values())
    floor_step = l_step + sum(other_gaps_us.values())
    out = {
        "central": dict(ar_us=round(c_ar, 2), ar_tok_s=round(rate(c_ar), 1), mtp_step_us=round(c_step, 1),
                        mtp_tok_s=round(taus["central_pinned_pooled"] / c_step * 1e6, 1),
                        mtp_tok_s_at_agentic_4p69=round(4.69 / c_step * 1e6, 1)),
        "low": dict(ar_us=round(l_ar, 2), ar_tok_s=round(rate(l_ar), 1), mtp_step_us=round(l_step, 1),
                    mtp_tok_s=round(taus["low_LMSYS_poetry"] / l_step * 1e6, 1),
                    mtp_tok_s_at_tau_3p649=round(3.649 / l_step * 1e6, 1)),
        "high": dict(ar_us=round(h_ar, 2), ar_tok_s=round(rate(h_ar), 1), mtp_step_us=round(h_step, 1),
                     mtp_tok_s=round(taus["high_pilot_agentic_median"] / h_step * 1e6, 1)),
        "rtl_as_built_floor": dict(ar_tok_s=round(rate(floor_ar), 1), mtp_tok_s_at_tau_3p649=round(3.649 / floor_step * 1e6, 1),
                                   note="LOW plus the three further model-assumed fusions the RTL lacks (design needed); basis v41_rom.json proposal cycles, converted at 1.2 GHz"),
        "taus": taus,
        "tau_for_3000": dict(central=round(3000 * c_step / 1e6, 3), low=round(3000 * l_step / 1e6, 3), high=round(3000 * h_step / 1e6, 3)),
        "terms": [
            {"term": "collectives (C1 4-owner board group)", "us": 66.7, "class": "MEASURED RTL (8 seeds + 2 corners, W15 link layer)"},
            {"term": "field / chain / kv / hops / PAR2 crossings", "us": [116.0, 162.0, 21.5, 24.6, 31.3], "class": "MODEL (S58 graph; PAR2 boundary model-only)"},
            {"term": "same-x phase merge", "us": round(phase_merge_us, 1), "class": "MODEL assumes merged; RTL bench MEASURED 270-275 cycles/phase saved, bit-exact; emitter + runtime token pending; exposure ASSUMED"},
            {"term": "q-element pipelining", "class": "MEASURED exact (L=2/3); routes R_cap0/R_cap1 running on ot-epyc1tb, no STA yet; zero-latency fix FAILED -316/-437 ps post-CTS, so a recurrence cycle is a live risk (LOW)"},
            {"term": "CDC 1.2/0.9", "class": "MEASURED successor FIFO 1.6-1.7 cycles, closes SS/FF; parent integration pending (central credit)"},
            {"term": "draft cost", "class": "MEASURED structure ratio on HBM composer (0.117 AR) replaces assumed 0.075"},
            {"term": "tau", "class": "UNQUALIFIED: pinned pooled 3.649; pilot agentic median 4.69; LMSYS third-party GSM8K 5.24 / Poetry 2.91 / Arena-Hard 3.78 is a verify window, not accepted length"},
            {"term": "verify expert collisions", "class": "MODEL issues x6 per node; measured mean max multiplicity 4.19 <= 6, so covered"},
            {"term": "clock", "class": "LOW case: streaming 1.0 GHz and serial chain 0.75 GHz (+%.1f us AR)" % clock_ar_us},
        ],
    }
    return out


# ---------------- DeepSeek-V4.1 HBM comparator (W19 fused, 1M) ----------------
def ds_hbm():
    ar_us = 442.14
    coll, fetch = 240.46, 5.33
    rest = ar_us - coll - fetch
    step = 700.9 + 51.9        # measured-union verify P6 + real DSpark draft (d2aff19ef)
    l_ar = 458.46 + rest * (1.2 / 1.0 - 1) + rest * (0.9 / 0.84 - 1)   # unfused + clock + HBM derate on non-collective part
    l_step = step * l_ar / ar_us
    h_ar = ar_us - 11.6        # H5 TMEM epilogue (GPU-real feature), consolidation.json
    h_step = step - 11.8
    return {
        "central": dict(ar_us=ar_us, ar_tok_s=round(rate(ar_us), 1), mtp_step_us=round(step, 1), mtp_tok_s=round(3.649 / step * 1e6, 1),
                        mtp_tok_s_at_agentic_4p69=round(4.69 / step * 1e6, 1)),
        "low": dict(ar_us=round(l_ar, 2), ar_tok_s=round(rate(l_ar), 1), mtp_step_us=round(l_step, 1), mtp_tok_s=round(2.91 / l_step * 1e6, 1),
                    mtp_tok_s_at_tau_3p649=round(3.649 / l_step * 1e6, 1)),
        "high": dict(ar_us=round(h_ar, 2), ar_tok_s=round(rate(h_ar), 1), mtp_step_us=round(h_step, 1), mtp_tok_s=round(4.69 / h_step * 1e6, 1),
                     mtp_tok_s_at_tau_3p649=round(3.649 / h_step * 1e6, 1)),
        "terms": [
            {"term": "265 collectives", "us": coll, "class": "MODEL on W15 measured product-port fits"},
            {"term": "wide top-k select", "class": "MEASURED 419 cycles (select alone)"},
            {"term": "routed-expert fetch", "us": fetch, "class": "MODEL"},
            {"term": "grouped o-reduce", "class": "EXTRAPOLATED"},
            {"term": "SM shape", "class": "line-rate priced, not measured"},
            {"term": "verify union / draft", "class": "MEASURED union (30 agentic traces) and real DSpark structure"},
            {"term": "owner/ACK/CDC bridge", "class": "UNPRICED (open, H-bridge owners)"},
        ],
    }


def main():
    q, qh, d, dh = qwen_rom(), qwen_hbm(), ds_rom(), ds_hbm()
    ratios = {
        "qwen_rom_ar_over_hbm_ar": dict(central=round(q["central"]["tok_s"] / qh["central"]["tok_s"], 2),
                                         low=round(q["low"]["tok_s"] / qh["high"]["tok_s"], 2),
                                         high=round(q["high"]["tok_s"] / qh["low"]["tok_s"], 2)),
        "qwen_rom_ar_over_hbm_dflash": dict(central=round(q["central"]["tok_s"] / qh["dflash_b16"]["tok_s"], 2),
                                             low=round(q["low"]["tok_s"] / (qh["dflash_b16"]["tok_s"] * 0.958 / 0.9), 2),
                                             high=round(q["high"]["tok_s"] / (qh["dflash_b16"]["tok_s"] * 0.84 / 0.9), 2)),
        "qwen_basis_caveat": "ROM is TP-4 over 2 packages / 16 stacks; the HBM row is one 2-die, 8-stack package. At equal package count the bandwidth-bound HBM AR would be up to ~2x (minus a cross-package all-reduce), i.e. ratios roughly halve.",
        "ds_rom_ar_over_hbm_ar": dict(central=round(d["central"]["ar_tok_s"] / dh["central"]["ar_tok_s"], 2),
                                       low=round(d["low"]["ar_tok_s"] / dh["high"]["ar_tok_s"], 2),
                                       high=round(d["high"]["ar_tok_s"] / dh["low"]["ar_tok_s"], 2)),
        "ds_rom_mtp_over_hbm_mtp_same_tau": dict(central=round(dh["central"]["mtp_step_us"] / d["central"]["mtp_step_us"], 2),
                                                  low=round(dh["high"]["mtp_step_us"] / d["low"]["mtp_step_us"], 2),
                                                  high=round(dh["low"]["mtp_step_us"] / d["high"]["mtp_step_us"], 2)),
    }
    verdicts = {
        "qwen_rom": dict(target=3000, verdict="MEETS (conditional on near-HBM attention + reticle fit)",
                         margin_central=round(q["central"]["tok_s"] / 3000 - 1, 3), margin_low=round(q["low"]["tok_s"] / 3000 - 1, 3),
                         without_near_hbm="MISSES (2,793; KV-fill-service bound, best floor 3,245)",
                         vs_historical_11325="MISSES (0.51x central)",
                         dominant=["reticle fit of the r2 floorplan (Part B)", "near-HBM attention physical closure + R=8 area + 261-cycle HBM notice", "1.2 GHz closure (1.0 GHz case still meets)"]),
        "qwen_hbm": dict(target=None, verdict="NO TARGET WRITTEN", note="bandwidth-bound; central 880.5 AR, 2,671 DFlash"),
        "ds_rom": dict(target="3000 accepted tok/s after MTP", verdict="AT RISK",
                       margin_central=round(d["central"]["mtp_tok_s"] / 3000 - 1, 3), margin_low=round(d["low"]["mtp_tok_s"] / 3000 - 1, 3),
                       margin_high=round(d["high"]["mtp_tok_s"] / 3000 - 1, 3),
                       vs_spec_ar_4599="MISSES (0.52x central)", vs_spec_mtp_9500="MISSES (0.33x central)",
                       dominant=["acceptance tau (needs >= %.2f at central step; pinned 3.649, LMSYS Poetry 2.91)" % d["tau_for_3000"]["central"],
                                 "same-x phase-merge emitter gap (+73 us/step if not delivered)", "clock ceiling (1.0/0.75 GHz: +14%)"],
                       levers=["land the class-A phase-merge emitter option (zero area, measured bit-exact) + runtime layer A/B",
                               "cut the MTP verify step: ROM verify costs 2.7x AR (1,150 vs 422 us) because 6 positions issue x6 on the field; a multi-column (m=2) field element or verify-only lane doubling is the lever",
                               "bind a qualified agentic tau (pilot median 4.69 gives 4,076)"]),
        "ds_hbm": dict(target=None, verdict="NO TARGET WRITTEN",
                       note="central MTP 4,847 at tau 3.649 EXCEEDS the ROM's 3,172: on DS the ROM/HBM MTP ratio is ~0.65x"),
    }
    print(json.dumps(dict(schema="opentallas.risk-perf-ledger.v1", status="MODEL_ONLY_LEDGER_NOT_QUALIFICATION",
                          targets=TARGETS, qwen_rom=q, qwen_hbm=qh, ds_rom=d, ds_hbm=dh, ratios=ratios,
                          verdicts=verdicts, sources=SOURCES), indent=1))


if __name__ == "__main__":
    main()
