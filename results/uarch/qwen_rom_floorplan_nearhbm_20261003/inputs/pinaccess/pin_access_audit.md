# Macro pin access against the ASAP7 track grid: audit and fix

Date: 2026-10-03. Branch `claude/rom-macro-pin-access-20261003`. Tool: `tools/check_macro_track_alignment.py`, with `tools/test_check_macro_track_alignment.py` (7 tests). Machine-readable results are in `pin_access_audit.json`. No P&R was launched.

## 1. Root cause

The track grid is ORFS `platforms/asap7/openRoad/make_tracks.tcl`, byte-identical to the archived `results/uarch/*/inputs/make_tracks.tcl`:
- M4 runs horizontally on y = 0.012 + n·0.048.
- M5 runs vertically on x = 0.012 + n·0.048.
- The site is 0.054 × 0.270.

The generator (`tools/mem_compiler/views.py`) builds every ROM and SRAM abstract the same way:
- Signal pins are 24 × 24 nm M4 squares on the left and right edges.
- Pin centres are at local y = 0.780 + k·0.096, which is 0.012 mod 0.048, so they sit on a track in R0 when the origin is 0 mod 0.048.
- Height is snapped only to the 0.270 row (`height_snap_um`).

Mirroring about X maps y to H − y. The pins therefore stay on track in every orientation only when **H ≡ 2·0.012 = 0.024 (mod 0.048)**. A height that is a multiple of the pitch is not enough, because the M4 track offset is pitch/4.

| Abstract (catalog, 21) | H mod 0.048 | Origin rule (nm mod 48) R0 / MX / MY / R180 |
|---|---:|---|
| ot_rom_4096x274_m8, 4096x266, 4096x72, sram_2rw_512x64 | 30 | 0 / **42** / 0 / **42** |
| ot_rom_8192x{274,266,104}_m8, sram_1rw_256x64 | 12 | 0 / **12** / 0 / **12** |
| ot_rom_16384x266_m16, sram_1rw_2048x128_m4 | 42 | 0 / **30** / 0 / **30** |
| sram_1r1w_{128x256,256x256,64x512} | 0 | 0 / **24** / 0 / **24** |
| sram_1r1w_1024x256, sram_1rw_2048x128_r2c2 | 6 | 0 / **18** / 0 / **18** |
| sram_1r1w_512x128 | 36 | 0 / **36** / 0 / **36** |
| ot_rom_1024x72_m8 (H = 20.52) | 24 | 0 / 0 / 0 / 0, the only invariant abstract |
| ot_hbm3e_phy, …_aw30_e8p5 (M5 pins on top edge) | W mod 48 = 0 | 0 / 0 / **24** / **24** |
| ot_hbm3e_phy_v41x, …_aw30 (v1) | — | no legal origin in any orientation: pins fall on 24 phases (a known v1 defect) |

- **18 of 21** catalog abstracts put every pin off-track in MX and R180 under a "0 mod 0.048" origin snap. The two HBM PHYs do the same in MY and R180.
- Outside the catalog, the p-die macros (`ot_pdie_coll`, `serdes`, `tile_io`, `ucie`, `tile_bk`) and `ot_hbm3e_phy_v41x_s4` declare `SYMMETRY X Y` and are mirror-variant in the same way.
- The hardened element LEFs are R0-only and on-grid.
- The v2 HBM generator comment says "width a multiple of 0.432, so MY/R180 keep pins on track". That is false for the 0.012 offset: MY needs origin ≡ 24 nm.

**Joint row and track rule.** A legal Y-mirrored origin exists on the row grid for every macro, at one point per 2.16 µm. For the 4096-row ROMs that point is **y ≡ 0.81 µm (mod 2.16)** in MX and R180, and y ≡ 0 in R0 and MY. The A_r2 hook's 89.37 µm satisfies this.

**Other checks:**
- **Pin area.** Every pin is 576 nm², below the M4 minimum area of 2,000 nm². The router has to patch it. Edge pins can extend outward, so this is not the trigger.
- **Blockages.** OBS covers M1–M3 completely and starts 48 nm inside the edge on M4. That meets M4 spacing, so the pins are not blocked; access is M4 in-plane or a V4 drop from M5.
- **Secondary x-phase issue.**
  - The ROM widths are ≡ 0 mod 0.048, so only one edge can have an M5 track crossing its pins at a given x origin.
  - The four residual TT DRCs (M2 spacing at the macro edge, in a8_su, p2, p5 and p8) all sit on the edge with no M5 crossing.
  - W ≡ 0.024 mod 0.048 fixes this. The r2c2 SRAMs already meet it.

## 2. Historical failures re-examined

Each case was re-evaluated with the tool at the hook-snapped origins (`historical_placements.json`).

| Run(s) | Utilisation | Orientations | Off-track pins | Failure | Class |
|---|---:|---|---:|---|---|
| a6 | 0.745 | R0 | 0 | Routed with 0 DRC; WNS −484 ps (TT) | timing |
| a8_su, p2, p5, p8 | 0.72–0.79 | R0, MY | 0 | Routed with 1–2 M2 DRCs at the ROM pin edge; WNS −46 to −573 ps (TT) | timing, plus x-phase edge DRC |
| p12q4, p12q5 | ~0.83 | R0/MX/MY/R180 | 576 | GRT-0116 congestion (40,570 and 2,648 overflow) | genuine density |
| p12q6 | ~0.83 | same | 576 | DPL-0033 at CTS | legalisation |
| p12q8, frontpar_r1 | 0.83 | same | 576 | FLW-0024 (place density > 1.0) | density setting |
| **p12q9** | ~0.83 | same | 576 | GRT clean; DRT-0255 on u_rom1 (MX) | **mirrored pin access** |
| c8 (BF16 pair) | — | same | 576 | DRT-0255 on u_rom1 (MX); 576 DRT-0419 = all MX and R180 pins | mirrored pin access |
| qframe A_r1 / B_r1 | **0.60 / 0.48** | same | 576 | GRT overflow 0; DRT-0255 on u_rom1 | mirrored pin access |
| window_bank4, attn_sram_bank | — | R0, unsnapped | 821 per macro (8–16 nm) | DRT-0255 ×12 and ×5 | same class (unsnapped origin) |

**Verdict on the "density ceiling 0.375":**
- Only 1 of the 10 in-band runs (p12q9) failed by mirrored pin access.
- Mirrored pin access is, however, the only failure seen below 0.83, and it occurred at 0.48–0.60.
- Every R0/MY run at 0.72–0.79 completed detail route, with at most 2 edge DRCs, and failed on **timing**.
- Genuine congestion appears only at 0.83, on SS with hold buffering.
- So 0.375 is the highest *closed* macro run, not a routability ceiling. The routing evidence does not rule out an element frame at about 0.70, but timing must close first.
- Causation of the mirrored-pin DRT-0255 is strongly indicated but not yet proven:
  - In 4 of 4 runs the failing nets are only on MX/R180 macros, at densities from 0.48 to 0.83.
  - The w10_c8 diagnosis rightly notes that every pin rect still intersects a track.
  - A_r2 and C_r1 (snap fix only) are the controlled test.
- This root cause was already derived on 2026-10-01 (`results/uarch/w10_wake_pinaccess_contract_review`: required phase 42 nm). The hooks were never changed.
  - Still latent on main: `physical/abi3/w10_wake_q_place.tcl`, `w10_wake_column_place.tcl`, `physical/v41x_window_bank4_macro_place.tcl` and `physical/v41x_attn_bank_post_macro_place.tcl`.

## 3. Fixes

**(a) Generator: the robust fix.** Memory compilers normally guarantee on-grid pins in every declared orientation. Two rules achieve that here:
- Choose H ≡ 0.024 (mod 0.048), so one origin rule serves all four orientations.
- Choose W ≡ 0.024 (mod 0.048), so the M5 crossing works on both edges.

Pricing per DS-V4.1 die (8,192 weight ROMs and 14,336 cfg ROMs):

| Option | Weight ROM area | cfg ROM area | Per-die total | q frame |
|---|---|---|---|---|
| H 62.910 → 62.952 (+42 nm, off the row grid) | +0.067 % | +0.067 % | 0.043 + 0.023 = **0.066 mm²** | — |
| H → 63.720 (row-grid multiple; k ≡ 4 mod 8 rows) | +1.29 % | +1.29 % | 0.83 + 0.44 = 1.27 mm² of macro area | **zero**: the 2.16 µm stack pitch already reserves 64.8 µm |
| W → W + 0.216 (two-edge M5) | — | — | 0.11 + 0.19 mm² | — |
| Pin shift of +3 nm | 0 | 0 | 0 | — |

The pin shift is free, but it moves the rule for every orientation to origin ≡ 45 nm, so it is not preferred. Regenerating any abstract changes pinned LEFs, so it needs a new macro version, not an edit.

**(b) Orientation-aware snap in every hook.** This is immediate and changes no LEF.
- Snap the y origin to (0.012 − c_o) mod 0.048, where c_o is the oriented pin centre, jointly with the row grid. The tool's `snap_joint_nm` and `check_placement` give the value.
- Gate every POST_MACRO_PLACE hook with an assertion that no pin is off-track, so the failure appears at floorplan rather than hours later in DRT.
- OpenROAD's macro placer is designed to snap pin-layer pins to tracks for each orientation. The custom hooks bypass it.

**(c) Restrict orientations to R0 and MY.**
- This costs only the y-position of the rom1 pin band. The pins are on the vertical edges, so escape is sideways either way.
- Drop R90 from the generated SYMMETRY: every R90-family orientation has no legal origin.

**ICG gating check (−230 ps at SS).**
- The cause is in the RTL:
  - `cg_en` includes `walk_busy`, which comes from gclk flops at 614 ps latency.
  - The ICG CLK pin sits at the root, at 88 ps.
  - So 526 ps of skew is spent before any logic.
- Fix:
  - Drive ENA from a single flop on ungated clk with no logic after it: a registered enable computed one cycle ahead, with DRAIN + 1. The added cycle has to be priced in the model.
  - Also clone the ICG per register cluster (bit-exact), so each ICG's CLK latency approaches its leaves'.
- A flop-to-ICG path with no logic leaves roughly +100 ps at the current latencies (estimate from 833 + 88 − 614 − 60 − clk→q − setup; not measured).

**High-fanout path n_c → fw_q1 (data 959 ps).**
- `hit_q` enables 532 fw_* flops through a buffer chain.
- Replicate the class_match/hit compare per 64-bit slice with `(* keep *)`. That is 8 copies, about 20 µm², with zero latency and bit-exact results.
- Alternatively, gate the fw bank with local ICGs.
- Both fixes are independent of the frame, so the q element will not close at SS at any density until they land.
