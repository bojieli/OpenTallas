# SM matvec price at the die's physical HBM bandwidth (owner 2026-10-12, option 1)

The simulator charged every SM weight line at one line per cycle. An SM line is 136 B (the 1,088-bit DS line, `hgi_sim.ds_native.SM_LB`), so that price assumed **136 B/cycle per SM**.

The die cannot supply that. Per the owner's decision, the price is corrected to the bandwidth the die physically has. No HBM bandwidth is added to the die. HBM4 appears below only as a sensitivity row for the paper.

## Derivation (one named constant)

The constant is `tools/w19_hbm_token_compose.py: SM_HBM_BYTES_PER_CYCLE`. It is built from the die's own HBM parameters:

| quantity | value | source |
|---|---|---|
| HBM3E stacks a die | 4 | ARCH_SPEC_V41 / ARCH_SPEC_QWEN3 (4 stacks a die; unchanged by B2) |
| rate a stack | 1.0 TB/s | same |
| peak a die | 4.0 TB/s | 4 × 1.0 |
| sustained fraction | 0.95 | vehicle A measured (results/rtl/qwen_hbmacc_p8191_20261004); `hgi_sim/calibration.json` hbm.bytes_per_cycle = 3,166.7 B/cycle |
| clock / SMs | 1.2 GHz / 32 | `F_FAST`, `N_SM` |
| **peak a SM** | 4.0e12 / 1.2e9 / 32 = **104.17 B/cycle** | `SM_HBM_PEAK_BYTES_PER_CYCLE` |
| **sustained a SM (price floor)** | 104.17 × 0.95 = **98.96 B/cycle** | `SM_HBM_BYTES_PER_CYCLE` (× 32 = 3,166.7, equal to the calibration) |
| line price factor | 136 / 98.96 = **1.3743** | `sm_line_cycles(lines) = lines × max(1, 136 / 98.96)` |

**Where the floor applies.** It applies in `SMTable.op` (`hbm_floor=True` by default), so every consumer of the SM line table picks it up:
- the DS walk (`dshbm_1m_allmeasured.walk`);
- `hgi_sim.ds_hgi.WalkCost`, for both the batched expert-slot rule and unbatched matvecs;
- `hgi_sim.perf`;
- `w19_hbm_token_compose`.

The raw line count is still available as `hbm_floor=False`. The model-vs-RTL comparison in `dshbm_dspark_model_compare.py` uses it, because the RTL bench counts raw lines.

For Qwen, `hgi_sim.timing.cost` (SM) already took max(lane lines, die-average stream). It now also floors the busiest SM's rows at bw / 32.

**Other classes checked.** ATT, DMA, the ROW_GATHER read/write and the IDX key stream already price at the die's 3,166.7 B/cycle or at a measured HBM stream. No other class assumes more than the physical bandwidth.

## Before / after (S2 schedule, same records)

Reproduce with `python3 -m throughput_budget.hbm_bw_reprice --qwen --out ../results/arch/hbm_bw_reprice_1012/reprice.json`, run from `tools/` (about 40 s). The output is in `reprice.json`.

| row | B/cycle/SM | SM batched expert (800 rec) | SM other (295 rec) | SM.MATVEC total (1,095 rec) | DS token cycles | **DS-V4.1 tok/s, HBM, 1M** |
|---|---|---|---|---|---|---|
| before (1 line = 1 cycle) | 136 (implied) | 22,720.0 | 81,248.3 | 103,968.3 | 565,569 | **2,121.8** |
| **after (design)** | **98.96** | 31,224.5 (×1.3743) | 95,651.0 | 126,875.5 | 576,702 | **2,080.8** (−1.9 %) |
| HBM4-class, paper sensitivity only | 128.65 (5.2 TB/s × 0.95 / 1.2 GHz / 32) | 24,018.8 | 83,447.8 | 107,466.6 | 567,101 | 2,116.0 |

- **DS target.** The table rate is still 2,208.1 tok/s. `price_scale_to_target` moves from 0.9609 to 0.9423 (`throughput_budget_20261010/budget.json`, regenerated).
- **The token loses only 1.9 %.** SM pricing rises 22,907 cycles a token, but the token only gets 11,133 cycles longer: S2 hides most of the SM stream behind other units.
- **Qwen3-8B, HBM, 8K: unaffected.** It stays at 945.5 tok/s (1,269,120 cycles) before and after. Its SM records are INT8 fmt3 (160 B per 128 codes over two beats = 80 B/cycle/SM, which is below 98.96). The BF16 lines were already bound by the die stream.
- **The HBM4 row is not a design change.** It is for the paper only (owner: no 5.2 TB/s on the die). Even at 128.65 B/cycle/SM, a 136-B line still binds, at ×1.057.

## SM.MATVEC throughput qualification (1.10 × the corrected price)

| scope | corrected price | qualify (≤ 1.10×) |
|---|---|---|
| whole token, 1,095 records | 126,875.5 cycles | **≤ 139,563 cycles** |
| per record (mean) | 115.9 | ≤ 127.5 |
| tb_hgi_sm_tput matched subset (1,015 records, excluding wq_b ×40 and wo_a ×40) | 87,969.6 (was 72,728.4) | **≤ 96,766.6** |
| batched expert record, L lines | L × 1.3743 | ≤ L × 1.5117 cycles (1.512 cycles a line) |
| FP4 w1 / w3 (K 5,120, 24 lines) | 32.98 | ≤ 36.3 |
| FP4 w2 (K 2,304 ×2 rows, 32 lines) | 43.98 | ≤ 48.4 |
| FP8 slot-6 w1 / w3 (40 lines) | 54.97 | ≤ 60.5 |
| FP8 slot-6 w2 (48 lines) | 65.97 | ≤ 72.6 |
| unbatched record | lines × 1.3743 + drain + first access / overhead (walk rule) | 1.10 × that |

**The last bench, regraded.** The committed bench (`results/rtl/hgi_unit_tput_20261010/sm/report.json`, 2,392,946 cycles on the matched subset) was 32.90× the old price. Against the corrected price it is **27.20×**, which is the number `build.py` now uses.

An SM unit that streams one line every 1.374 cycles is at price; it does not need one line a cycle. This is the throughput the SM streams must design to.
