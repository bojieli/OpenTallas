# DS-V4.1 HBM switch collective latency: a sourced range

**SUPERSEDED 2026-10-04** by the AUTHORITATIVE switch scenarios (measured H100 NVLS, Tomahawk Ultra + our protocol): `results/uarch/hbm_switch_latency_authoritative_20261004/` (AUTHORITATIVE) (sources `results/measured/h100_nvls_20261004/`). This record is kept unchanged as the literature range. Its replay command now emits the measured record.

MODEL ONLY. Owner decision (2026-10-04): the DS-V4.1 HBM switch collective latency is now a sourced range instead of the single quoted 250 ns switch core. That core gave alpha = 2 x 209 + 250 = 668 ns, and W15 measured the fixed collective terms at AR 823.6 ns and AG 777.0 ns. The new range covers one 32 KB all-reduce across 48 packages in one NVL72-class tier of 18 switch chips, hardware path only. The sources are in `switch_latency_research.md`, copied verbatim, section 2.

| Scenario | AR per collective (KP4 / light FEC) | Mechanism |
|---|---|---|
| low | 0.65 / 0.49 us | push-mode in-switch reduce, SUE/UALink-class endpoints |
| central | 1.40 (range 1.3-1.5) / 1.24 us | the same mechanism with measured GB200 endpoint constants (0.79 us one-way + L2) |
| high | 3.25 (range 3.0-3.5) / 2.62 us | NVLS as exposed today: barrier + ld_reduce RTT + multicast store (4 traversals) |
| retry tail | +0.2-0.5 us per LLR event | p99-p99.9 only. One event per token is 0.05-0.11% of the W19 AR token, so it is not in the median rows. |

Rules:
- Every collective's FIXED term is replaced. Slope and bytes terms are kept.
- W19 pass: 265 collectives (40 AR + 225 gather-like). The DSpark draft is ASSUMED to have 26.3 collectives with the same mix.
- Primary rows price every collective at the AR range. `gathers=gather_note` rows use the research note's gather range as a sensitivity: 0.60 / 1.20 / 2.0 us, where the high value is DERIVED.
- FEC: the sourced range is taken as the published rack-cable path, which is KP4 class. `light` removes (209 - 130) ns on every SerDes leg crossed, 2 per traversal, which puts the switch legs in the same light-FEC 130 ns class as the ROM board links. The light rows are therefore the FEC-matched ROM:HBM comparison. The kp4 rows are the unequal comparison, kept for reference. Light FEC is not qualified for rack-cable reach.
- MTP: tau 4.159 (owner 6-class equal blend, gamma 5, `blend_owner6.json`). Step = verify(P=6) + draft.
- The 200K rows apply the W19 record's context ratio to the passes and add the collective delta unscaled.
- Designs:
  - ablation = W19.
  - accelerator = the frozen HA firm ladder (R0c..R6a) without R2, because the switch is kept and the direct mesh was owner-rejected. It is UNVALIDATED.
  - measured composition = W19 minus the measured, non-rejected rung gains (R5a 13.381 us, NOT adopted).
  - GPU-faithful R0 = every boundary is a 1.43 us grid sync.
- ROM = `results/rtl/dsrom_wavefront_verify_20261004/record.json` (S81 AR + wavefront-occupancy MTP), light FEC.
- Defaults are unchanged. `--hbm-switch-latency {low,central,high} [--hbm-fec light]` opts the legacy fabric lump in: the ~188 collectives x 0.668 us become ~188 x the scenario (125.9 us becomes 122.5 / 263.9 / 612.5 us at KP4). It does the same for the `--hbm-accel` record.

Replay: `python3 tools/uarch_model.py --hbm-switch-latency-range --out results/uarch/hbm_switch_latency_range_20261004/model.json`

### 1M (ROM S81 + wavefront: AR 2466.2, MTP 8036.0 tok/s, light FEC)

| HBM design | FEC | AR tok/s: W15 baseline / low / central / high | MTP tok/s (tau 4.159): baseline / low / central / high | ROM:HBM AR (low-central-high) | ROM:HBM MTP (low-central-high) |
|---|---|---|---|---|---|
| Ablation (W19) | light (matched) | 2,498 / 2,742 / 1,775 / 1,077 | 5,885 / 6,230 / 4,694 / 3,232 | 0.90 - 1.39 - 2.29 | 1.29 - 1.71 - 2.49 |
| Ablation (W19) | kp4 | 2,262 / 2,459 / 1,652 / 913 | 5,525 / 5,828 / 4,462 / 2,827 | 1.00 - 1.49 - 2.70 | 1.38 - 1.80 - 2.84 |
| Accelerator (firm ladder, switch kept) | light (matched) | 2,779 / 3,083 / 1,912 / 1,126 | 6,508 / 6,932 / 5,082 / 3,411 | 0.80 - 1.29 - 2.19 | 1.16 - 1.58 - 2.36 |
| Accelerator (firm ladder, switch kept) | kp4 | 2,489 / 2,731 / 1,770 / 948 | 6,071 / 6,438 / 4,811 / 2,963 | 0.90 - 1.39 - 2.60 | 1.25 - 1.67 - 2.71 |
| Measured composition | light (matched) | 2,585 / 2,846 / 1,818 / 1,093 | 5,999 / 6,357 / 4,765 / 3,266 | 0.87 - 1.36 - 2.26 | 1.26 - 1.69 - 2.46 |
| Measured composition | kp4 | 2,332 / 2,543 / 1,689 / 924 | 5,625 / 5,939 / 4,527 / 2,853 | 0.97 - 1.46 - 2.67 | 1.35 - 1.77 - 2.82 |
| GPU-faithful R0 | light (matched) | 1,152 / 1,201 / 969 / 716 | 3,416 / 3,529 / 2,977 / 2,313 | 2.05 - 2.54 - 3.44 | 2.28 - 2.70 - 3.47 |
| GPU-faithful R0 | kp4 | 1,099 / 1,143 / 932 / 640 | 3,291 / 3,396 / 2,882 / 2,098 | 2.16 - 2.65 - 3.86 | 2.37 - 2.79 - 3.83 |

### 200K (ROM S81 + wavefront: AR 2574.1, MTP 8342.1 tok/s, light FEC)

| HBM design | FEC | AR tok/s: W15 baseline / low / central / high | MTP tok/s (tau 4.159): baseline / low / central / high | ROM:HBM AR (low-central-high) | ROM:HBM MTP (low-central-high) |
|---|---|---|---|---|---|
| Ablation (W19) | light (matched) | 2,504 / 2,748 / 1,777 / 1,078 | 5,897 / 6,243 / 4,701 / 3,235 | 0.94 - 1.45 - 2.39 | 1.34 - 1.77 - 2.58 |
| Ablation (W19) | kp4 | 2,266 / 2,464 / 1,654 / 913 | 5,536 / 5,839 / 4,469 / 2,830 | 1.04 - 1.56 - 2.82 | 1.43 - 1.87 - 2.95 |
| Accelerator (firm ladder, switch kept) | light (matched) | 2,785 / 3,090 / 1,914 / 1,127 | 6,522 / 6,947 / 5,090 / 3,415 | 0.83 - 1.34 - 2.28 | 1.20 - 1.64 - 2.44 |
| Accelerator (firm ladder, switch kept) | kp4 | 2,494 / 2,736 / 1,772 / 948 | 6,083 / 6,451 / 4,818 / 2,966 | 0.94 - 1.45 - 2.71 | 1.29 - 1.73 - 2.81 |
| Measured composition | light (matched) | 2,590 / 2,853 / 1,820 / 1,094 | 6,011 / 6,371 / 4,773 / 3,269 | 0.90 - 1.41 - 2.35 | 1.31 - 1.75 - 2.55 |
| Measured composition | kp4 | 2,337 / 2,548 / 1,692 / 925 | 5,636 / 5,951 / 4,534 / 2,856 | 1.01 - 1.52 - 2.78 | 1.40 - 1.84 - 2.92 |
| GPU-faithful R0 | light (matched) | 1,154 / 1,203 / 971 / 717 | 3,422 / 3,536 / 2,982 / 2,316 | 2.14 - 2.65 - 3.59 | 2.36 - 2.80 - 3.60 |
| GPU-faithful R0 | kp4 | 1,101 / 1,146 / 933 / 640 | 3,298 / 3,403 / 2,887 / 2,101 | 2.25 - 2.76 - 4.02 | 2.45 - 2.89 - 3.97 |
