# Macro track-alignment fix: replay

Date: 2026-10-03. Branch `claude/macro-alignment-fix-20261003`.

This fixes the defect found by the audit in `results/uarch/macro_pin_access_audit_20261003`. Generated abstracts put signal-pin centres at 0.012 mod 0.048 µm. A mirrored copy therefore stays on the M4/M5 tracks only if the flipped dimension is ≡ 0.024 mod 0.048. The placement hooks snapped every origin to 0 mod 0.048 regardless of orientation.

No pinned file was edited. Every change is a new file or a successor.

## What was added

| Piece | Path |
|---|---|
| Orientation-aware snap and pre-route assert (Tcl, OpenDB) | `physical/common/ot_macro_track_snap.tcl` |
| Standalone assert hook for any run (POST_TAPCELL) | `physical/common/ot_macro_track_assert_hook.tcl` |
| Successor hooks for the four defective hooks | `physical/abi3/w10_wake_q_place_aligned.tcl`, `physical/abi3/w10_wake_column_place_aligned.tcl`, `physical/v41x_window_bank4_macro_place_aligned.tcl`, `physical/v41x_attn_bank_post_macro_place_aligned.tcl` |
| Launch path with the gate (default off) | `tools/run_abi3_physical_aligned.py --macro-track-gate` |
| Generator successor | `tools/mem_compiler/build_aligned_v2.py` |
| Aligned abstracts | `physical/asap7_memory_macros_v2/` (21 macros), `physical/asap7_v41x_pdie_macros_v2/` (6 macros), `physical/asap7_memory_macros_v2_ew/` (east/west-edge `ot_hbm3e_phy`) |
| Tests | `tools/test_ot_macro_track_snap.py` (checker, OpenROAD harness `physical/common/test_ot_macro_track_snap.tcl`, launch gate) |

### Snap library: `ot_mts::place inst x y orient ?status?`

- Reads the master's signal pins, W and H, and the platform `MAKE_TRACKS` file.
- Computes the legal origin residues for the requested orientation.
- Intersects them with the site and row grid.
- Takes the nearest legal point that overlaps no placed macro and stays inside the die.

The overlap check matters for stacked pairs. With v2 abstracts, the q-pair's MX ROM requested at 63.45 µm lands at 64.80 µm, the next legal point above the R0 ROM. With v1 abstracts it stays at 63.45 µm, the same point the A_r2 fix found.

### Assert: `ot_mts::assert_on_track`

- Checks every signal-pin centre of every placed CLASS BLOCK instance against the block's own `dbTrackGrid` lines.
- Uses `dbITerm::getBBox`, so it shares no code with the snap's orientation table.
- Any off-track pin raises `OT_MACRO_TRACK_ASSERT FAIL` at floorplan time.

### Launch gate: `--macro-track-gate`

1. Audits every `--macro-view` abstract with `tools/check_macro_track_alignment.py`. An abstract with no legal origin in an allowed mirror orientation refuses the launch.
2. Refuses any of the four defective hooks and names its successor.
3. Appends `--step-tcl POST_TAPCELL=physical/common/ot_macro_track_assert_hook.tcl`.
4. Writes a gate record next to the launch receipt.

The gate then runs the unchanged `run_abi3_physical_persistent.py` or `run_abi3_physical.py`.

### v2 rule

- **H and W.** H ≡ W ≡ 0.024 (mod 0.048), at the smallest growth on the 1 nm grid.
- **Symmetry.** SYMMETRY is `X Y`. R90 is dropped because no rotated orientation has a legal origin.
- **HBM PHYs.** Pin blocks start on the 0.048 grid. The v1 PHY centred its block, which no width can make mirror-invariant.
- **v1 V4.1 PHYs.** The two defective v1 PHYs are re-emitted under their own names by the legal writer at their 12.0 mm edge.

**Outcome.** One origin rule, x = y = 0 mod 0.048 on the site and row grid, puts every pin on track in R0, MX, MY and R180. On every ROM and SRAM, M5 now crosses the pins of both edges, which removes the secondary x-phase edge DRCs.

Macro names are unchanged. Select a v2 set with `--macro-view NAME=physical/asap7_memory_macros_v2/NAME`.

### East/west HBM PHY

This was requested for the Qwen ROM near-HBM B2-EW frame (`claude/qwen-rom-floorplan-nearhbm-20261003` @ b4593fb82). The macro is `ot_hbm3e_phy` turned on its side:

- Size is 833.496 × 12000.120 µm.
- The 9,209 controller pins are on M4, on the west edge, at 0.192 µm pitch.
- Place it R0 on the die's east edge and MY on the west edge. MX and R180 are also legal.
- The area delta against the v1 footprint is +92 µm² per PHY (+0.001 %), or +368 µm² for 4 PHYs.

The catalog PHY's top-edge M5 pins have no legal rotated orientation. That is why this is a separate abstract and not an R90 placement.

## Area pricing (v2 minus v1, per macro)

`physical/asap7_memory_macros_v2/index.json` holds these figures, including the row-grid alternative for every macro.

| Macro | v2 W x H (µm) | dW / dH (nm) | Δ area µm² (%) |
|---|---|---|---|
| ot_hbm3e_phy | 12000.120 x 833.490 | 24 / 0 | +20.004 (0.000%) |
| ot_hbm3e_phy_v41x | 12000.120 x 833.760 | 24 / 270 | +3260.036 (0.033%) |
| ot_hbm3e_phy_v41x_aw30 | 12000.120 x 833.760 | 24 / 270 | +3260.036 (0.033%) |
| ot_hbm3e_phy_v41x_aw30_e8p5 | 8500.056 x 1177.200 | 24 / 0 | +28.253 (0.000%) |
| ot_rom_1024x72_m8 | 37.176 x 20.520 | 24 / 0 | +0.492 (0.065%) |
| ot_rom_16384x266_m16 | 237.192 x 119.640 | 24 / 30 | +9.986 (0.035%) |
| ot_rom_4096x266_m8 | 121.848 x 62.952 | 24 / 42 | +6.628 (0.086%) |
| ot_rom_4096x274_m8 | 125.304 x 62.952 | 24 / 42 | +6.773 (0.086%) |
| ot_rom_4096x72_m8 | 38.040 x 62.952 | 24 / 42 | +3.107 (0.130%) |
| ot_rom_8192x104_m8 | 52.296 x 119.352 | 24 / 12 | +3.492 (0.056%) |
| ot_rom_8192x266_m8 | 122.280 x 119.352 | 24 / 12 | +4.332 (0.030%) |
| ot_rom_8192x274_m8 | 125.736 x 119.352 | 24 / 12 | +4.373 (0.029%) |
| ot_sram_1r1w_1024x256_m2_r2c2 | 174.744 x 70.488 | 0 / 18 | +3.145 (0.025%) |
| ot_sram_1r1w_128x256_m1_r2c2 | 94.824 x 41.064 | 0 / 24 | +2.276 (0.059%) |
| ot_sram_1r1w_256x256_m2_r2c2 | 172.824 x 41.064 | 24 / 24 | +5.133 (0.072%) |
| ot_sram_1r1w_512x128_m4_r2c2 | 174.120 x 29.736 | 24 / 36 | +6.981 (0.135%) |
| ot_sram_1r1w_64x512_m1_r2c2 | 171.288 x 77.784 | 0 / 24 | +4.111 (0.031%) |
| ot_sram_1rw_2048x128_m4 | 118.824 x 65.640 | 24 / 30 | +5.139 (0.066%) |
| ot_sram_1rw_2048x128_m4_r2c2 | 122.904 x 66.168 | 0 / 18 | +2.212 (0.027%) |
| ot_sram_1rw_256x64_m4_r2c2 | 66.312 x 17.832 | 0 / 12 | +0.796 (0.067%) |
| ot_sram_2rw_512x64_m4_r2c2 | 130.920 x 34.872 | 24 / 42 | +6.335 (0.139%) |
| ot_hbm3e_phy_v41x_s4 (p-die) | 3000.120 x 208.440 | 42 / 0 | +8.755 (0.001%) |
| ot_pdie_coll (p-die) | 225.048 x 110.712 | 30 / 12 | +6.022 (0.024%) |
| ot_pdie_serdes (p-die) | 250.056 x 2250.216 | 36 / 36 | +90.008 (0.016%) |
| ot_pdie_tile_bk (p-die) | 789.432 x 978.504 | 6 / 24 | +24.817 (0.003%) |
| ot_pdie_tile_io (p-die) | 789.432 x 978.504 | 6 / 24 | +24.817 (0.003%) |
| ot_pdie_ucie (p-die) | 260.808 x 1652.424 | 42 / 24 | +75.660 (0.018%) |
| ot_hbm3e_phy (east/west) | 833.496 x 12000.120 | 6 / 24 | +92.004 (0.001%) vs v1 turned |

### Per DS-V4.1 ROM die

The die carries 8,192 `ot_rom_4096x274_m8` and 14,336 `ot_rom_4096x72_m8`.

| Option | Δ macro area per die |
|---|---:|
| v2 as emitted (H +42 nm, W +24 nm) | **+0.100 mm²** (0.0555 + 0.0445) |
| Height-only fix (the audit's figure) | +0.066 mm² |
| Row-grid alternative (H 63.72 µm, priced, not emitted) | +1.31 mm² |

These figures are macro area only; they do not re-pack the floorplan.

**Frame consequence.** A stacked R0/MX v2 pair needs a 64.80 µm stack pitch: the next legal row point above a 62.952 µm macro. The w10 q-pair frames that place rom1 at 63.45 µm must either keep the v1 abstracts, with the aligned hook, or grow by 1.35 µm.

## Replay

```
git checkout <frozen SHA>
python3 tools/mem_compiler/build_aligned_v2.py --check-only      # rebuilds all three v2 sets, byte-compares: CHECK PASS
python3 tools/check_macro_track_alignment.py physical/asap7_memory_macros_v2/*/*.lef \
    physical/asap7_v41x_pdie_macros_v2/*/*.lef physical/asap7_memory_macros_v2_ew/*/*.lef --fail-on-offtrack
python3 -m pytest -q tools/test_ot_macro_track_snap.py tools/test_check_macro_track_alignment.py
```

The OpenROAD harness cases need docker with `openroad/orfs:latest`, and take about 10 minutes.

## Tests

| Area | What is checked |
|---|---|
| Checker | All 27 v2 abstracts and the east/west PHY have rule [0] on every pin layer in R0, MX, MY and R180, with no rotated symmetry. Every ROM and SRAM has M5 crossing on both edges. The v1 view digests are unchanged. |
| OpenROAD, v2 sets | `ot_mts::place` puts every pin on track: 0 off-track, both targets, every orientation. |
| OpenROAD, v1 catalog | The same holds, except the two defective v1 V4.1 PHYs, which return NO_LEGAL_ORIGIN as expected. |
| Negative: defective snap | The hooks' naive MX snap leaves all 288 pins of a v1 `ot_rom_4096x274_m8` off-track, and the assert sees them. The invariant `ot_rom_1024x72_m8` shows 0. |
| Negative: 6 nm shift | Moving a legal placement by 6 nm in x and y trips `OT_MACRO_TRACK_ASSERT` on every macro of both sets. |
| Stacked pair | Placements do not overlap: v2 puts rom1 at 64.80 µm, v1 at 63.45 µm, both 0 off-track. |
| Launch gate | Refuses a dead PHY and a defective hook; passes v2 and appends the assert; warns on a v1 mirror-variant abstract. |

## Validation run

This reruns the block that previously failed by pin access: `ot_chip_v41x_attn_sram_bank_phy`.

- **Original record.** `results/physical_abi3/asap7/chip/v41x_attn_sram_bank_phy`: DRT-0255 ×5, with the macro origin 16 nm off-track.
- **Setup.** The original argv (TT, 0.92 ns, die 250 × 140 µm), launched through `tools/run_abi3_physical_aligned.py --macro-track-gate` with the successor hook `physical/v41x_attn_bank_post_macro_place_aligned.tcl`.
- **Where it ran.** Local, in the pinned worktree at c8b518b3e, with distinct nicknames `v41_att_sram_bank_align_{v1,v2}`.

| Run | Abstract | Macro placed | Assert (POST_MACRO_PLACE, POST_TAPCELL) | DRT-0419 | Detail route | Signoff (TT) |
|---|---|---|---|---:|---|---|
| align_v1 | v1 `ot_sram_1r1w_256x256_m2_r2c2` | MX at (44.010, 43.200), snapped from 44/44 | PASS: 821 pins, 0 off-track | 0 | **0 violations**, 79 s | pass: setup and hold 0 violations, DRC 0 |
| align_v2 | v2 (172.824 × 41.064) | MX at (44.010, 44.280) | PASS: 821 pins, 0 off-track | 0 | **0 violations**, 74 s | pass: setup and hold 0 violations, DRC 0 |

RTLMP chose MX for the macro; the hook keeps the placer's orientation and snaps the origin for it. The same block and floorplan that hit DRT-0255 ×5 at a raw 44.0 µm origin now routes clean with either abstract.

This is a TT pathfinding run on a characterization block, and it is no SS signoff claim. The records are in `validation_attn_sram_bank/`:

- `physical_v{1,2}.json`
- the launch receipts
- the gate records
- `assert_v*.txt`
- the detail-route logs (gzipped)

