# Qwen3-8B ROM rate: workload and KV-format identity

Reviewed tree: origin/main dcba5c0ab. Machine-readable version: `workload_identity.json`.

## Verdict
The finite calendar (361.07 / 358.60 / 358.01 us) and the historical 8,460 / 6,222 tok/s rows already describe the same workload:
- 8K window, decode position 8191;
- batch 1, AR;
- per-element unscaled FP8 E4M3 KV.

They differ only in **KV delivery**. The historical rows treat the KV as on core, or streamed at PHY rate and fully hidden. The calendar sends it through a 7 x 64 B on-die fill network at 1.2 GHz. The KV bytes are not over-charged. The published *headline* (atlas and HEADLINE_BUNDLE: 10,874 / 18,720) describes a different machine: the TP2 two-reticle package with DFlash.

## Q1. Published figures and their workloads
| Figure | Where | Ctx / pos | Decode, batch | KV fmt | KV delivery |
|---|---|---|---|---|---|
| 8,460 | MICROARCH_MODEL.md:706,923,929; tools/uarch_model.py:5612-5614 -> qwen_tp_point :4890 | 8192 / 8191 (as_built replays T_ctx-1, arch_budget_qwen3.py:752-781) | AR, 1 | fp8 (arch_budget_qwen3.py:62; uarch_model.py:2241-2244) | Not in the cycles: "KV on core" (arch_budget_qwen3.py:758). It appears only as a saturated bound (uarch_model.py:4923) |
| 6,222 | MICROARCH_MODEL.md:707,923,929; uarch_model.py:5620-5636 | 8192 / 8191, **calibrated at position 0** (uarch_model.py:5571, :5595 ctx=1) | AR, 1 | fp8 | Same as 8,460 |
| 9,368 TT / 9,384 (KV read 41.9 us, "binding compute chain") | MICROARCH_MODEL.md:703,1003 | 8192 | AR, 1 | fp8 | 4 x 0.9 TB/s, overlapped |
| 10,874 AR / 18,720 DFlash / 7,859 / 6,680 / 11,921 | ARCHITECTURE_ATLAS.html:210,238,276-277,1278,1417; HEADLINE_BUNDLE.md:38-72; MICROARCH_MODEL.md:341 | 8192 (qwen3_budget.json:16-21) | DFlash + AR, 1 | fp8 | max(compute, kv) at 7.2 TB/s (arch_budget_qwen3.py:601-615); **TP2 package, stale** (atlas :638 adopts option C TP4, AR only) |
| 361.07 / 358.60 / 358.01 us | credit_allocator model-r4.json:1874; credit17 model-r3.json:1900; beat_retirement model-r3.json:1675 | 8192 / 8191 (prose "source8191" only; fields exist only in rate_risk model_r3.json:42,61 and uarch_model_qwen_kv_bank_groups.py:401) | AR implied, 1 | fp8 (uarch_model_qwen_kv_rate_risk.py:211) | Cold-per-layer lease; 7 lanes x 64 B (model-r4.json:73,98); adopted_rate null (:1891) |
| TP4 token 50994 | qwen_rom_TP4_terminal_20261002/terminal_manifest.json:11,93 | **1 / 0** (zero KV reset) | -, 1 | fp8 (original_terminal.json:8; ot_qwen_rom_rt_die_w12.sv:134) | Host-serviced |

EVIDENCE_LEDGER.md, PROGRAM_STATUS.md and INTEGRATED_PHYSICAL_PLAN.md publish no Qwen ROM rate.

## Q2. The 281 us vs 42 us gap
- **Minimal bytes.** At position 8191 a decode must read K and V for every layer: 36 x 2 x 2 heads/die x 128 x 8191 x 1 B = **150,976,512 B/die**.
  - No layer re-reads another layer's KV.
  - No TP die re-reads another die's KV: GQA gives 2 KV heads per die.
  - The calendar reads **150,690,816 B** (model-r4.json:1880). That is the logical total minus a K-tail of 2 tiles per head kept in SRAM and a forwarded current V (rate_risk.py:226-229).
  - It also writes 156,672 B (:1881).
  - The figure 150,847,488 is not KV read bytes. It is 4,713,984 commands x 32 B: RD 4,709,088 + WR 4,896 (:137,140).
- **The difference is the fill network, not the bytes.**
  - The historical model: 150.69 MB / 3.6 TB/s = 41.9 us, hidden under compute.
  - The calendar: the busiest of 7 fill lanes carries 9,380 beats per layer. 36 x 9,380 / 1.2 GHz = **281.4 us** (model-r4.json:77-86). That network carries 448 B/edge = 537.6 GB/s, against a PHY of 3.6 TB/s. The PHY only needs 113 GB/s per stack (:1985).
  - The 7 lanes were dimensioned to the 3,000 tok/s target (:66), not to the PHY. Matching the PHY would take about 47 lanes.
- **Where the rest of the 361 us goes:**

| Component | us |
|---|---:|
| Fill floor (busiest lane) | 281.4 |
| Fill-period inefficiency: credits, refresh, arbitration | 74.5 |
| Last layer's attention | 2.6 |
| Non-layer work | 2.6 |
| **Total** | **361.07** |

- **The lease adds little.** The next layer's fill starts at the previous layer's all-grants, so attention overlaps it. There is no double-charging.

## Q3. KV format
Every component uses **FP8 E4M3, per element, unscaled, 1 B/element**:
- **Golden:** tools/hdc_golden.py:261-280, landed in 8a91421a3.
- **TP4 RTL:** KV_FP8(1).
- **Quality contract:** ACCEPTABLE, PPL -0.14% at 8K, MMLU -0.4 pt; results/quality/qwen3_8b_deployment_arithmetic.json:52.
- **Calendar:** FP8.

This is the adopted contract (arch_budget_qwen3.py:62; qwen3_budget.json:18; atlas :638).

Four statements still say BF16 and are stale:
- arch_budget_qwen3.py:62 comment;
- arch_budget_qwen3.py:1518;
- quality json :14;
- ot_hdc_kv_stream.sv:81, where HBM_FP8 defaults to 0 and the SRAM is BF16.

If the KV were BF16, the off-chip read would be 301,381,632 B, the fill floor **562.8 us** and the PHY floor 83.7 us.

## Q4. Required identity
Every Qwen ROM rate record must carry these fields:
- `decode_mode=AR`, `speculation=none`, `batch_users=1`
- `context_window_positions=8192`, `decode_position=8191`, `position_basis=worst_case_last_of_window`
- `kv_format=fp8_e4m3_per_element_unscaled`, `kv_bytes_per_element=1`
- `kv_home=attached_hbm_4_stacks_per_die`, `kv_on_die_reuse=k_tail_2_tiles_per_head_plus_current_v_forward`
- `kv_delivery_policy` (`cold_per_layer_lease` | `prefetch_layer_ahead`)
- `kv_offchip_read_B_per_die_token=150690816`, `kv_write_B_per_die_token=156672`
- `fill_lanes`, `fill_bytes_per_edge`, `stream_clock_hz`
- `rate_basis` (`finite_calendar_conditional` | `analytical_overlap` | `rtl_measured`)
- `numerical_evidence_position=0`

Two rates may be compared only when all fields match.

**Places where mismatched identities are compared today:**
- CURRENT_WORK_HANDOFF_2026_10_03.md:118 compares 8,460/6,222 with the calendar, and mislabels the command bytes as KV bytes.
- qwen_kv_beat_retirement_composition.py:52 and uarch_model_qwen_kv_beat_retirement.py:233-247 screen 3000/6222/8460 against the calendar.
- MICROARCH_MODEL.md:706-707/923/929 apply a position-0 calibration to a position-8191 chain.
- MICROARCH_MODEL.md:1003 says "binding compute chain", which assumes PHY-rate fill.
- The atlas and HEADLINE_BUNDLE publish TP2 + DFlash headlines; MICROARCH_MODEL.md:341 puts 10,874 (TP2) beside 9,851 (option C).
- results/uarch/qwen_rom.json:335 has 8460.12 for TP2 G4608: the same value as the option C row, a different configuration.
- Atlas :778 promises a layer-ahead prefetch into a 19.3 MB ring; the calendar uses the lease (model-r4.json:73).
- In the TP4 terminal record, original_terminal.json:3 says "G=5,120 TP-2" while its design_point is tp=4.
- The calendar records carry no identity fields.
