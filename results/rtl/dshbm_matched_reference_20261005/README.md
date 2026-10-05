# Matched DS HBM reference for the DS ROM gate (1M context, position 1,048,575)

`composition.json` is built by `tools/dshbm_matched_reference.py`. It re-walks the executed TP-96 program of the inherited reference (`results/rtl/dshbm_1m_allmeasured_20261004/composition.json`: 460.053 µs AR, 888.077 µs MTP step) and reproduces that reference exactly before changing anything. Every term that is not named below is the inherited term, unchanged.

## Gate figures

| | AR µs/token | MTP step µs (τ-independent) | MTP tok/s at τ 4.159 (sensitivity τ 3.8879) |
|---|---:|---:|---:|
| Inherited reference (the review's) | 460.053 | 888.077 | 4,683.2 (4,377.9) |
| Corrected only (C1–C3 measured, no levers) | 566.864 | 1,104.861 | 3,764.3 (3,518.9) |
| **Gate reference at 1.2 GHz** (best credited configuration per mode) | **474.808** | **1,050.638** | **3,958.5** (3,700.5) |
| Gate reference at today's closing clocks | 596.027 | 1,289.398 | 3,225.5 (3,015.3) |

**Target (owner 2026-10-05).** The DS ROM continues to closure, targeting ROM AR ≤ 474.808 µs **and** ROM MTP step ≤ 1,050.638 µs; the comparison is a measured checkpoint for the paper, not a kill switch. The MTP step does not depend on τ; MTP tok/s uses τ 4.159 (owner 6-class workload blend, adopted 2026-10-05), with the published V4.1 3.8879 as the sensitivity in parentheses.
- Each HBM figure is the best credited configuration for its own mode, so the bar for ROM is the harder one.
- The AR figure comes from `corrected+wg+fused_su0.9`.
- The MTP figure comes from `corrected+wg+su12`. The fused chains are not measured at 6 positions (see L3 below), so they add nothing to MTP.

## Ladder at the target clocks

SM, attention, fast DUs, collective endpoint and HBM run at 1.2 GHz. The quantisers and serial DUs stay at 0.9 GHz.

| Row | AR µs | MTP step µs |
|---|---:|---:|
| inherited | 460.053 | 888.077 |
| corrected (C1 + C2 + C3) | 566.864 | 1,104.861 |
| + L1 expert workgroup | 524.097 | 1,062.094 |
| + L2 SU at 1.2 GHz (m6a5, wire stages 7 / 8) | 527.865 | 1,050.638 |
| + L3 fused SU chains (`matched`) | 476.178 | 1,050.638 |
| L1 + L3, SU chains kept at 0.9 GHz | **474.808** | 1,062.094 |
| *sensitivity:* L2 with the unreachable 0.9 GHz wire stages 4 / 5 | 522.938 | 1,046.410 |
| *sensitivity:* `matched` without the hc_post fusion | 487.178 | 1,050.638 |

## Ladder at today's clocks

Inherited clocks: SM 1,030.9, SU 638.6, attention 881, collective endpoint 394.5, router 621.5 MHz. With L2, the SU domain runs at its m6a5 lanes' clock today, 999.2 MHz on the r2r basis (`su_m6a5/lane_clock.json`).

| Row | AR µs | MTP step µs |
|---|---:|---:|
| corrected | 728.085 | 1,383.824 |
| + workgroup | 678.303 | 1,334.042 |
| + SU m6a5 at 999.2 MHz | 662.104 | 1,289.398 |
| `matched` | 596.027 | 1,289.398 |
| L1 + L3, SU at 638.6 MHz | 596.082 | 1,334.042 |

## C1–C3: where the inherited composition under-counts, and the measurement

**Where.** In `tools/dshbm_1m_allmeasured.py` `walk()`, each flush group of matvecs is priced as `lines + drain`, using the weight-line count from `w19_hbm_token_compose.SMTable.op`.
- **C1, unused issue slots.** `lines + drain` assumes every issue slot carries a line. The group-slot issue actually runs waves of 8 (row, group) items × 8 chunk steps, so a partial last wave leaves holes.
- **C2, separate op drains.** Consecutive expert slots are batched: `pend["cyc"] += lines`, with one drain for the whole batch. But `ot_hbm_accel_issue` accepts `start` only when not busy, so each op drains on its own.
- **C3, activation loading.** Every SM bench writes the x store before t0. The only x cost charged is the barrier's 16-cycle x tail (`BARRIER_CYC` 78 = 62 + 16).

**Measured.** All three were measured together on the minimum component.
- **Element:** one SM, the 1.2 GHz successor `ot_hbm_accel_sm_v` ENABLE=1 from main e1bf44f09, with NC 8. Its own +12 drain and +19..27 start-to-done are therefore inside every cycle count, and its +4 barrier crossing is added to the barrier.
- **Ops:** the busiest SM's op sequence, run back to back.
- **Bench and driver:** bench `rtl/test/tb_hbm_accel_sm_v_seq.sv`, driver `tools/dshbm_matched_sm_seq.py`, records in `sm_seq/`, run under Verilator 5.050.
- **x loading:** each op whose x is not resident writes only its used x addresses, 2 beats each for AR and 10 for P6 (6 active columns). The documented 1 cycle passes before `start`.
- **Ordering:** `start` waits until the previous op is done; the descriptors are posted ahead (warm stream).
- **Coverage:** every distinct shape of the token is covered: `ar_l20` and `p6_l20` run the whole layer-20 sequence; `wg`, `other`, `p6_wg` and `p6_other` cover the workgroup op, the engram fp8 K 6144, the ratio-2 indexer wq_b and the head.
- **Exactness:** every result of every op matches the golden bit for bit. All 6 records PASS with 0 mismatching ops.
- **Warm stream:** a record's first op is used only when its shape occurs nowhere else, because the bench ring has not yet run ahead at that point.
- **Reuse:** the x-reuse rule (same vector, same format and K as the previous op on the SM; never a w2 or engram) gives 571 load phases. That is the same count the review's activation audit found.

**SM correction at AR, 1.2 GHz: +106.81 µs.**

| Component | µs |
|---|---:|
| C1: issue holes (24.908 µs, equal to the review's audit) + start/handshake protocol (8.11 + 0.92 µs) | +33.94 |
| C2: per-op drains 66.915 µs, against the 18.585 µs the inherited flush groups charged | +48.33 |
| C3: 571 x loads | +27.97 |
| Barrier: 16-cycle x tail replaced by the measured load, +4 successor crossing per group | −3.43 |

**MTP (P6).** The x loads are 137.94 µs, because 6 columns × 3,152 bits through the as-built 2,048-bit port make 10 beats per address. The remaining SM terms are the same as for AR.

## Shared exact levers credited to HBM

**L1, expert workgroup.** The 12 routed gate/up matrices run as one row set.
- Each of 24 SMs streams 12 contiguous rows of one matrix: one static descriptor, no gather.
- The op is measured: fp4 K 5,120 R 12 takes 396 cycles, bit-exact. It replaces 12 ops of 135–139 cycles each.
- AR: −42.77 µs. MTP: −42.77 µs.

**L2, SU at 1.2 GHz** (bd935b346 f12 units).
- The same 38 chains were re-measured at MLAT 6 / ALAT 5 with hub wire stages 7 / 8. All are exact (`su_m6a5/`).
- The lane build is on unmerged branch `origin/claude/hbm-fmax-su-20261004` (@3d0e34db5).
- AR: +3.77 µs. The deeper pipeline cancels the clock gain.
- MTP: −11.46 µs.
- No m6a5 lane closes yet: light lane r2r −4.76 ps, side lane −167.45 ps, softplus −112.85 ps.

**L3, fused SU chains.** The DS ROM engines were re-run on the HBM SU wiring (HUB_IN 6 / HUB_OUT 8, derived as ceil(4 × 748 / 504) and ceil(5 × 748 / 504)), at full shape on the cached golden 1M operands, all exact (`su_fused/`).

| Fused engine | Replaces | Cycles | AR on path |
|---|---|---:|---:|
| norm hc (+ quant) | hc_pre_norm + quant, final_norm | 236 at 1.2 GHz | 43.83 → 15.93 µs |
| norm q ∥ kv (+ RoPE and QDQ) | q_norm_kv_row + quant | 210 | 15.87 → 7.00 µs |
| SwiGLU (+ route weight and quant) | swiglu | 133 | 5.91 → 4.43 µs |
| hc_post NG256 | hc_post | 57 | 14.85 → 3.80 µs |

- **hc_post caveat:** this engine is exact only on its M5A4 lane, and that lane is REJECT_SS (−52.47 ps). Its M6A5 lane is not exact. The figure therefore favours the lever; the sensitivity without it is in the ladder.
- **P1 only:** the fused benches run one position, so MTP keeps the measured SU chains.
- **ROM side:** none of these levers is adopted on ROM yet (physical admission BLOCKED). For the gate, credit them on both sides or on neither.

## Still modelled or unvalidated

These items are listed in `composition.json` `unvalidated`. Unless stated otherwise, each one favours HBM.

- **Inherited vendor and model terms:**
  - Tomahawk-Ultra PHY, switch and cable: 115.168 µs (vendor budget)
  - Striping tails: 39.75 µs
  - MTP union SM / fetch increments: 47.74 + 28.45 µs (W19 model). The union SM term does **not** carry C1–C3, so the MTP correction is a lower bound.
  - LOCAL_REPEAT issue fraction at P6
  - Draft 45.28 µs and seed 3.567 µs
  - Off-path judgements
- **Index path on borrowed blocks.** Per the coordinator, main 96ed22b21 `attn/closure.json`: no HBM-accelerator RTL instantiates the index path. These terms are measured on the shared `ot_hdc_v41x_*` blocks and are not HBM-die equivalents. Their 1.2 GHz closure on the HBM side is OPEN. They total 8.915 µs AR (`index_path`):

  | Term | µs | Block |
  |---|---:|---|
  | du:index_q | 1.787 | HBM SU chain + shared actquant |
  | du:index_scores | 2.085 | `ot_hdc_v41x_idx_array` W11 |
  | du:topk_local | 1.897 | `ot_hdc_v41x_sel` |
  | du:cand_local | 0.353 | `ot_hdc_v41x_sel_cand` |
  | select:96x512 | 2.792 | `l20_index_topk` |

- **x-broadcast network depth (root → 32 x stores).** Not priced. The load is measured at the element's write port only.
- **P6 x loads through the as-built zero-padded port.** A format-masked port is not credited, because it is not built.
- **Workgroup layout and steering.** The 12-row-per-SM expert layout and the steering of SMs by router id are not built.
- **SM element route OPEN.** The leaves, issue and bulk copy close at 0.833 ns, but the element as a whole does not (`hbm_accel_fmax_inventory_20261004/sm/closure.json`). Today's rows therefore keep 1,030.9 MHz.
- **GU x load not hidden.** The 49-cycle GU x load could hide under routing; that overlap is not credited.

## Replay

Heavy steps run on a remote host only. On the host, put the Verilator 5.050 tools on `PATH`.

```
python3 tools/dshbm_matched_sm_seq.py run --seq {ar_l20|wg|other} --nc 8 --active 1 --out sm_seq/<seq>_nc8_a1.json
python3 tools/dshbm_matched_sm_seq.py run --seq {p6_l20|p6_wg|p6_other} --nc 8 --active 6 --out sm_seq/<seq>_nc8_a6.json
python3 tools/dshbm_matched_reference.py      # light: composes from the committed records
```
