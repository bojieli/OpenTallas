# smh_xs_ref_p45m (ot_hbm_accel_smh_xs) -- kit notes

## hxh (HBM-SMHXS-HOLD, REFILL-1330, 2026-10-19)

Predecessor hf5bt (`smh_xs_ref_p45m-hf5bt-e1b14e06f`, ot-epyc8) routed TT +60.74 / FF -45.75 / DRC 0; hold ECO rc=9
(least-bad pass FF -0.71 after 9,233 cells) -> NEEDS_RTL.

FF hold classification (daemon `cl/path_summary.json`, `w18_sta_ff.log`, 1,467 violating D pins):

| class | paths | worst | cause |
|---|---|---|---|
| reg->reg, cross-tree | 311 (w3b -> o_iw) + 13 (c3bd -> o_itag/ifirst/ilast/ifp4/u_ctle) | -45.75 | zero-logic delay-line hop launched on the TritonCTS mass tree (w3b[156] CLK 255.8 FF, 8 levels) and captured on the hf5bt boundary tree (o_iw[156] CLK 353.6, 11 levels); no common path (CRPR 0) -> 98 ps skew |
| IO reference | 54 (bk1 -> u_bkd2) + 22 (rl1 -> u_rl2) | -30.44 | input landing flops vs the median pin-flop reference (pin-flop band) + 25 ps uncertainty |
| hard-child clock reference | 0 | - | 4 SRAM clk pins clean |
| reset landing | 3 | +15.19 | met (2-stage relay) |

Fix (flow only; RTL, outline, macros, pin faces, SDC unchanged; 0 cycles):
- `bnd_branch.tcl` `ot_sv_all 1`: TritonCTS is not run; every load of the clock port net (15,345 registers + 4 SRAM clk
  pins) goes onto ONE balanced geometric tree from the stem beside the clk pin (8 levels = 256 leaves of ~60 sinks,
  BUFx24, repeaters > 80 um, equal buffer count per path). Every hop (delay line, boundary, macro) is intra-tree.
- route `hold_margin_ns` 0.01 -> 0.03 and `io_hold_margin_ns` 0.03 (KITS rule >= 0.025; SAFE-DESIGN 7 >= 0.03).

## SAFE-DESIGN checklist (owner 10-19)

1. Pins: PASS. The RTL registers every pin (input landing u_rl2 / u_bkv2 / u_bkd2 / u_ohl2 behind ot_hdly; outputs are the
   leaf's operand-stage registers; E-face control copy u_ctle). Flow pin registers stay off (they would add a cycle per link).
   Reset: WAIVED (coordinator to confirm): rst_a drives only the 4 async-reset pins of the RTL 2-stage reset relay
   (OT_SMH_RSTRELAY, u_rr / u_leaf.u_rr), removal slack +15.2 / +18.1; textbook_lint flags it because the relay is the landing.
2. Reach: PASS (textbook_lint reach 0.0 um; tile 302.4 x 157.68 um).
3. Fanout: PASS (set_max_fanout 32; E-face control is its own kept register; no >32-load critical cone in path_summary).
4. Depth: PASS (textbook_lint depth 283.4 ps; TT setup +60.74 routed).
5. Storage: x-store in 4 SRAM macros PASS. WAIVED (coordinator to confirm): the w / c row delay line
   (r0w -> w3 -> w3b -> iw, 788 b x 3 stages) keeps the row in step with the x-store read pipeline; an SRAM ring
   would need four more 256-b macros in a parent-fixed outline. Its hold risk was the cross-tree crossing, removed by item 7.
6. Floorplan: util 0.53, aspect 1.92, full-width S landing band PASS. WAIVED (coordinator to confirm): the 4 macros sit on
   the (0.432, 2.16) track lattice, not the 43.2 lattice: two 41.04-um macro rows with >= 20 um channels do not fit the
   43.2 lattice in the 157.68 um height that smh_tile_rp4lp fixes (needs 172.8 -> parent re-floorplan).
7. Clock: FIXED (one tree from a stem beside the clk pin, no second tree; pin-flop spread checked by the --cts gate at
   TT and FF <= 80; hold margin 0.03 core and IO).
8. Schedule: PASS (static, 0 cycles added).
