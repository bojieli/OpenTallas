# s81sl_vp: ot_s81sl_vp (S81 DV slice beat leaf: leaf store + hc_post, x5 per slice)

Owner S81-SLICE/VP (10-21). MAIN kit `s81sl_vp` (job tag s81sl_vp_s1); FALLBACK kit `s81sl_vp_fb` (define
`OT_S81SL_VP_RELAY`). Same outline (734.4 x 864.0), same pins, same macro / hard-child placement as c318a2024.

## Root cause of c318a2024 NEEDS_RTL (routed TT -102.46 ps, FF hold -7.82 ps)
- Worst setup: `g_ln[11].u_l/fault` (hard lane pin, 331 ps after the child clock pin) -> 16-way OR of the lane faults +
  9 local sources -> `fault` flop: 658 ps of OR4/OR5/AND5 + repeaters across the 4x4 lane grid. Logic + wire, not skew
  (capture clock was 113 ps later than launch).
- 100 of the top 319 violators: `cd_c[2]` (command op bit) -> NORM load decode -> 128 `n_pre` enables + their 128
  pin-side copies (`ot_prs_*`), i.e. one flop driving ~280 loads. Others of the same class: bank write-port selects
  (`xwv_c`, `cwa_c`, `hs_a[0]` -> SRAM `wd_in` / `w_mask_in`, 256 loads each), `dodd` -> cf, `dswp` -> hw_d, `xsw2` -> x_qd.
- Yosys merged the 4 identical per-column `lr` lane-feed copies with `hs_d` (same D): one flop drove 4 lanes ~520 um
  apart plus the bank write mux (`hs_d -> g_ln[].u_l/r1` violators).
- FF hold -7.8 (8 pins): short flop->flop pairs (hqd_c->hs_d, q0->yrow_d, the 33-deep write-back shift line) under a
  ~800-920 ps spine insertion; route hold repair stalled. I2R hold at sign-off was +3.9 (the -14.3 window was in-route).

## Fix (RTL a468afd8e..; ports and every data / schedule latency unchanged in MAIN)
- Fault: sources registered where they arise (per-lane lf/lv flops, per-row reduce, fold). Sticky fault +2..3 edges
  (diagnostic only, no compiler schedule use) -> slice calendar note: none.
- Kept copies (`(* keep *)`, ot_keep_regs.tcl) for every wide select, landed at the same edge: write port per 32-bit word
  group (8) + per bank address group (2); NORM decode per 16-bit n_pre group (8) + m_*; dswp/dodd/xsw2/wvl per word;
  cf capture one-hot per (step, word); lane_v per lane row; lr/ly per lane.
- Write-back valid 33-deep shift line -> 32-entry ring + output register; write-back index and HSTORE index tag lines ->
  burst counters (same values; bursts are contiguous and >= 5 cycles apart).
- 10 reset regions (<= ~33 loads per relay leaf); coefficient enables / relays unreset.
- FALLBACK only: registered relay on the lane feed (lr/ly/v) and lane outputs (o/vo/fault): POST write-back +2 edges
  (post_cmd_to_last_hw 63 -> 65, priced; slice calendar note if the fallback is bound).

## Benches (Verilator 5.050, ot-epyc5, committed witnesses results/rtl/s81_slice_1017/beat/vp_1021 and vpfb_1021)
base / baseimm PASS (post_cmd_to_last_hw 63/63 = unchanged; fallback 65/65); muttree / mutcoef / mutpostlast /
mutnormimm FAIL as expected (err 1 / 507 / 625 / 260).

## SAFE review (8 points, S81-SLICE/VP 10-21)
1. Pins: PASS - every input lands in a pin flop, every output leaves a flop (source-registered, pin_regs off); reset
   lands 2 stages (reset_landing). Faces <= 1.1 pins/um, full faces N/E/W.
2. Reach: MAIN waived - band -> lane-grid lane feed / write-back wires up to ~700 um single cycle (no logic in them; met
   in c318a2024 with repeaters); FALLBACK fixed - relay stage on both directions.
3. Fanout: fixed - kept copies, <= ~40 loads per select copy; reset leaves <= ~33; Yosys merge of lr prevented by keep.
4. Depth: fixed - the fault cone (989 ps) pipelined; remaining cones <= ~5 levels after the fanout split.
5. Storage: PASS - 16 KiB leaf store in 2 x ot_sram_1r1w_512x128 macros; write-back delay line -> ring; yrow_d (3 x 128 b
   alignment pipe) waived (data-moving pipeline, < 2 kb).
6. Floorplan: PASS - macros + 16 hard lanes on the 43.2 lattice (172.8 pitch, 58 um channels), one contiguous std-cell
   band y 676..864; util ~0.36 (below 40 %: outline fixed by the slice slot, not squeezed).
7. Clock: PASS - tile 0.73 x 0.86 mm < 1 mm, one region: balanced spine with hard-child insertion targets (208.8 ps);
   spread judged at the --cts gate; io_hold_margin 0.03.
8. Schedule / reset: PASS - static, no handshake; MAIN adds 0 cycles; FALLBACK +2 on POST write-back (priced above);
   reset only control / valid bits.

CODEX 10-21: source packaging fixed in fresh sparse WT. Original synth ring
implementation inferred nonconstant ALDFFE loads from variable-index writes
under two async resets. Constant-index per-bit ownership preserves the ring,
pointer, regional resets and latency. Existing SAFE review above applies;
collect existing exact benches and native census before accepting layout.

CODEX fanout successor after r4 native65/126: write-data/mask selectors are
8-bit groups; the first group per bank also owns the narrow bank address.
Coefficient and row-swap selectors are16-bit groups. Explicit keep on sticky
shared valid scalars prevents coalescing with an output-group replica.
Ring write pointers/valids are local per8entries; the read pointer remains
independent. tree3 reset forest preserves3-edge release with24leaves and
max8 children per reset group. Control/valid resets split into <=32-bit
leaves; data stays unreset. Existing MAIN63/FB65 POST budget unchanged.
SAFE1 registered seams unchanged;2 physical relay fallback unchanged;3 fixed
measured65/126 cones pending exact census;4 depth unchanged;5 ring and SRAM
unchanged;6 outline/lattice unchanged;7 clock/hold0.03 unchanged;8 static
schedule unchanged, only zero-edge control copies and3-edge reset forest.
