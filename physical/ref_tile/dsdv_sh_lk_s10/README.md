# dsdv_sh_lk_s10: structural successor of dsdv_sh_lk_sr9 (S81-SHLK, 2026-10-19)

## Why sr9 failed

The sr9 CTS gate runs were source 9f5e6ebba (E clock) and c0082d3cb (N clock), on ot-epyc8.

- **Setup timing:** TT -252 / -271 ps at placement RC. At the SS-report CTS stage, TNS was -315k ps and WNS was -316 / -334 ps.
  - Every worst path starts at `u_eng.ra_rpc[*]`. That is eight kept realigner pointer copies. Each copy rebuilt the FULL 512-bit `{ra[w1], ra[w0]}` pair and its byte shift, so each pointer bit drove about 1,000 loads.
  - These paths end at `sc_acc` or at the ox SRAM write data.
- **Macro to register:** -233 ps, from `u_sd` SRAM `rd_out` (TT clk->q 310 ps) through the head decode and credit check to `fault`. The next read address also depended on the pop.
- **Logic depth:** the textbook check flagged `ap0_pitch -> ap1_lp` at 26 levels, an estimated 884 ps.
- **Clock:** the root was at the E or N face, but the register mass sat in the W half of a 518-um tile. Insertion was 433..600 ps TT, a spread of 178 / 187 ps.
- **Routing:** GRT was still in extra iterations after 2 h. The cause was three pin-limited 176.9 x 81 um 16x546 macros with 825 contacts per face (10.2/um). Write data was split over both faces. Std cells were fragmented around the macros at 10% density.

## Structural changes

All changes are opt-in defines, set in this kit: `OT_S81_SH_APIPE9`, `OT_S81_SH_APIPE10`, `OT_S81_SH_SRAM` and `OT_S81_SH_RSZ`.

1. **APIPE 10 stream pipe** (`rtl/hdc/ingest/ot_hdc_kv_ingest.sv`):
   - **Stage P** captures, at the pop edge, the 40-byte ring window that holds the head. This is a 32:1 select of 8-byte ring granules. There are 10 kept pointer copies, each serving 32 window bits.
   - **Stage O** does the 8:1 fine byte select, using 8 kept offset copies with 32 bits each. It also does the ROWS tail mask, the IKEY scale substitution, and the `sc_acc` write.
   - A 4-entry output FIFO holds the result. Pops are credit-issued against the FIFO, so `w_rdy` is not in the pop cone. The FIFO is read through 9 kept one-hot copies.
   - A completion queue releases each done with its exact cumulative count, once that many sectors have been accepted.
   - The boot-end marker is delayed by the same 2 edges.
2. **Row address:** `ap1_lp` is now `local * pitch[2:0]` and `ap1_lph` is `local * pitch[4:3]`. Stage X does the three-operand add. No edge is added.
3. **svc FIFO** (`dsdv_sh_sd`): the popped head is registered straight from the macro (`h_q`). Decode, credit and fault are evaluated one edge later. This replaces the APIPE 9 payload hop, so `hw` timing is unchanged.
4. **Reset:** `ot_reset_sync` copies are rsh 8, rsi 40 and rsc 16. The top `u_rr` has 16 regions. `reset_relay_split.max_loads` is 32.
5. **Storage:** right-sized dual-clock masters, built by `tools/mem_compiler/build_sh_rsz_1019.py` with the unchanged compiler and the aligned-v2 wrapper.
   - The host FIFO uses two 16x257 masters (89.4 x 39.4 um).
   - The request and svc FIFOs each use one 16x289 master (99.1 x 44.0 um).
   - The native 32x64 banks (`OT_S81_SH_BANK64`) pass all benches but can't be used here. Their 17.304-um height is off the 0.27-um row grid, so they can't abut, and 16 lattice slots with 20-um channels would cost about 60k um2.
6. **Floorplan:** 302.4 x 194.4, versus 518.4 x 280.8 for sr9.
   - The 2x2 lattice macro grid is at x 43.2 / 172.8 and y 43.2 / 129.6.
   - The read faces point into the 30.5-um centre channel: MY on the W column, R0 on the E column. The write faces point to the W band (41 um) and the E band (28 um).
   - Fill is about 44%. The sibling kit `dsdv_sh_lk_s10w` runs in parallel with the same RTL and a 73.7-um centre channel, at 345.6 x 194.4.

## SAFE-DESIGN checklist (before gate)

| # | Item | Status |
|---|------|--------|
| 1 | Pins | PASS (source-registered). Every leaf input lands in a flop and every output is a flop (`pin_regs` opt-out kept). Reset lands in 2 registered stages (`reset_landing`), and `pin_reg_split` is kept. |
| 2 | Reach | PASS by construction. The tile is 302.4 x 194.4 and the longest Manhattan pin-to-pin path is about 497 um. Every seam is a flop at the pin, and the rung hop is landed at both faces (S to N is 194 um). |
| 3 | Fanout | Fixed. The realigner pointer now drives 32 loads per copy, down from about 1,000. The fine offset and FIFO read copies drive 32 each. Reset copies are limited to 32 loads (rsi D fanout is 40, on the release edge only). The mapped census must confirm these copies stayed separate. |
| 4 | Depth | Fixed. The `ra_rpc` cone is split into P and O stages, and the svc macro output is registered. `ap1_lp` is split. The `<=600 ps` claim needs the gate's textbook/STA to confirm it. |
| 5 | Storage | PASS. All runtime-indexed storage above 2 kb is SRAM. The 2,048-bit realigner ring stays in flops, read only through registered stage-P selects; it is at the threshold (waived as before). The FIFO is 4 x 288, the completion queue 8 x 40 and `sc_acc` 512 bits. |
| 6 | Floorplan | Macros are on the 43.2 lattice, channels are at least 30 um, and pin-face distance is at least 23 um. Aspect is 1.56. Fill of 44% is WARN-waived: the tile is macro/escape-bound, and std density is about 23% of the free area. Pins on full faces: N 1,207 / 302 = 4.0/um, S 2.8/um, W 3.1/um, E 2.3/um. Macro face contacts are 9.9/um, as for every master from this generator (the closed `dsdv_sh_sq` uses 10/um masters); 30-um channels are on the read faces. |
| 7 | Clock | One CTS root, `ck` at the E face. There are no hard children. `io_hold_margin` is 0.03. The CTS gate must measure pin-flop spread of at most 80 ps at TT and FF. |
| 8 | Schedule | Static, with no new credits on die seams; the engine FIFO credit is internal. The added cycles below are handed to the compiler and priced. |

## Added cycles, handed to the compiler and die schedule

- **Host stream:** each sector reaches the request FIFO 2 edges later (f_host -> s_hw: HSH 6 -> 8). Completion (done / t_host) and the boot-end marker are also +2. The svc FIFO adds +0, because the `h_q` edge replaces the APIPE 9 hop.
- **Rate:** unchanged at 1 sector per edge. In the hnp Verilator 5.050 bench (mixed clocks, RSZ), compared with APIPE 9:
  - raw: 1,074 ck, unchanged.
  - v41_win: 9,288 ck, about +12.
  - ikey_cross_sb: 4,634 ck, about +4.

## Benches (Verilator 5.050, fleet)

- **seqhost**, edge-exact lock-step against the goldens at HSH 8, seeds 1 and 2:
  - Passes with the plain SRAM, with `BANK64` (run `seqhost10b`) and with `RSZ` (run `seqhost10r`). The pair seeds, collide and stdrop runs also pass.
  - Mutants 1-10, 11 (`OT_ING_MUT_SPRH`) and 14 (`OT_S81_SH_MUT_HQSTALE`) are all caught. Lint is clean.
- **hnp** (`physical/sys_takeover/host_native_pipe_bench.py`): HBM image exact, visibility and done counts.
  - `pos10` passes for the flop, SRAM, `BANK64` and `RSZ` builds. It includes MSTALL 90 and a BOOTEND marker-ordering case.
  - Caught: `sprh10`, `spkind10`, `rac10`, `apbskip10`, `apstale10`, `apxskip10`, `banktail10`, `rszswap10` and `sramcur10`.
