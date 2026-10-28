# QC-A0-KITS-5 romleaf plan fix (2026-10-28)

COORD ruling: a0k3 (AP 688f9c1b2571) NOT signed off: pin-flop insertion TT 349.9 / FF 283.9 vs 250/202.5 +-40; related skew
TT 97.9/118.6, FF 92.8/111.2 all on the u_rom clock pin (early); fix in the PLAN, not an ECO.

## Diagnosis (CHECKED, probes in this dir on the a0k3 6_final.odb/.spef, TT RVT libs)
- ROM LIB `ot_rom_4096x266_m8_tt.lib` pin clk: NO max/min_clock_tree_path arc. rom_gen.timing_model puts the internal
  control/clock term (t_ctrl) inside clk->q and references setup/hold at the pin -> internal clock latency = 0; the ROM pin
  is balanced like a flop. OpenROAD CTS (26Q3) uses macro insertion delay by default (`-no_insertion_delay` not set) -> it sees 0.
- The ROM was early because the kit ran CTS with `-delay_buffer_derate 0.5` (generator default = half macro/register
  latency balance): placement RC ROM 253.8 vs flop mean 267.4; routed ROM 267.6 vs flops 325-382.
- Insertion 349 TT: entry (86.412,98.4) top band; 2200 flops W band 1444 / S band 606 / E 150; mean entry->flop 135 um.
  Path: 3 BUFx4 tap pads 75 ps, then a 198-um routed trunk (79 M5 + 119 M4; HPWL ~90) driven by the last BUFx4 pad:
  clkbuf_regs_0/Y 190 ps routed vs 125 placement RC -> 65 of the 82-ps placement->SPEF gap is this trunk.
## Plan fix (no ECO, no new gate)
- Slice a0_slices/ot_qwen_tile_romleaf.json: clock entry (86.412,98.4) -> (21.612,15.12) M5, same M5 track phase,
  S band under the ROM halo, at the logic corner; ROM clk pin (25.49,24.54) 13.3 um away; mean entry->flop 135 -> 42.6 um.
- Recipe: cts_args `-delay_buffer_derate 1.0` (full macro/register latency balance with the LIB insertion = 0).
## Estimate before build -> CTS trial (placement RC, CHECKED in 4_cts.odb of a kit copy)
- flops mean 259.5 (237.2..285.7), ROM 265.3 (was 50 ps early) ; tap balance it0 176 -> 3 pads -> 260; OT_TAP_CHECK OK.
- Routed estimate (UNCHECKED): a0k3 tree-below-root ratio SPEF/placement 1.12, trunk now ~0 -> TT mean ~270-285
  (<= 290), FF ~220-230 (x0.81 a0k3 FF/TT); ROM vs flop related skew ~20-40 (< 80); ROM->flop setup ~ +140 (was +217.7).
## Kit
ot_qwen_tile_romleaf_a0k5 (kit_hash cc11da503d8a7939) intel2:/srv/opentallas-scratch2/claude/qc-a0-kits-5-1028/romleaf/kits.
KIT_PREFLIGHT PASS 0; placed rc 0: RTL_LINT/SELRANGE PASS, FACE_GUARD 526/526, LEC EQUIVALENT 3348/3348; pins.json 527 (no clk).
AUTO-GEOM: same FAIL class as a0k3 (fill 0.093 / empty 0.794 = ROM leaf; GEOM-REVIEW-44 PASS-COND) + clock_reach 167.9
(was 175.2), GRT 0 ov. Render viewed: entry in the bottom-left logic corner beside the ROM clk pin; W column + S band + small E cluster.
