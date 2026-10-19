# dsdv_sh_lk_s10b: s10 with the SAFE fanout and depth fixes (S81-SHLK-B, 2026-10-19)

The kit uses the same floorplan, macros, pins, clock and reset as `dsdv_sh_lk_s10` (302.4 x 194.4). The `kit.env` files differ only in one define, `OT_S81_SH_S10B`. This kit runs in parallel with the live s10 and s10w gates. Whichever variant closes first under the checklist is bound.

## Why

The s10 gate synthesis (ot-epyc6 `ref_gate/dsdv_sh_lk_s10-20261019-115854`, `1_2_yosys.v`) broke two items of the SAFE checklist:

- **Depth:** the stage `st_row[0] -> st_row[31]` was about 690 ps over 19 levels. Yosys named that flop `s_grp[27]`. The stage is the 32-bit ripple increment that ABC left as an OR3 chain under its 770-ps target.
- **Fanout:** three nets drove 679 to 890 loads, counted through BUF/INV trees:
  - `AND2(u_hx.empty, hr_take)` drove 890 loads. It is the 444-bit `hr_d` load enable.
  - `u_eng.dq_rd[0]` drove 794 loads. It is the read select of the 4-entry descriptor queue into `st_d`, `st_left`, `st_row`, `st_beats` and `st_rem`.
  - `u_cx.rbin[1]` drove 679 loads. It is the 16:1 x 64-bit read mux of the completion FIFO.

## Changes (`OT_S81_SH_S10B`; no edge added)

1. **Descriptor queue.** There are 32 kept `dq_rdc` copies, loaded with `dq_rd` on the same edge. Copy k selects head bits 8k..8k+7.
2. **Registered host head.** `hr_d` is split into 33 slices of 16 bits. Each slice is loaded by `(!hr_vc[k] || hx_pop) && !hx_fempty_c[k]`. `hr_vc` holds kept copies of `hr_v`. `hx_fempty_c` holds kept copies of the FIFO empty flag, from the new `ot_dsdv_host_afifo_sram` `EC` port. `hx_pop` is the only shared term (about 33-66 loads, down from 890).
3. **Completion FIFO.** `u_cx` uses `RCOPY 32`: 32 kept read-address copies, each serving 2 bits. The copy-load enable fans out to 128 flops, which is below the 256 report threshold.
4. **Row and remaining counters.** `st_row` and `st_left` are split into a 4-bit low nibble and a 28-bit high word.
   - The low nibble steps in the cycle.
   - The high word takes a registered hi +1 / hi -1 (`sr_hp1` / `sl_hm1`).
   - That value is loaded with the segment (`s_disp`) and otherwise refreshed by a two-edge pipe: 14-bit halves, then a combine. The refresh holds for one edge after a load.
   - A carry needs 16 low steps, so the refresh always lands first. The result is exact for all 32 bits, wrap included.

### Benches (Verilator 5.050, fleet)

Witnesses are in `results/rtl/s81_shlk_s10b_1019`.

**seqhost HSH 8** passes the lock-step run on seeds 1 and 2, the pair seeds, collide and stdrop. Its `arrivals` counts are 1617, 1507 and 1606, the same as s10, which confirms the same edges.

**seqhost mutants:** 1-11 and 14 are caught, along with the new 16 (`HRC`) and 19 (u_cx `RCOPY` copy stall). Lint is clean.

**hnp pos10** (SRAM + RSZ + S10B) passes with the same cycle counts as s10: 1074, 9288, 538, 639, 1282 and 4634. It adds the case `raw_b16`.

**hnp mutants:**
- `dqc10`, `hpref10`, `hphold10` and `cxrc10` are caught. `hphold10` is caught by the `raw_b16` case, whose 16k-sector segments make the first `st_left` step borrow right after the load.
- `hrc10` is not exercised, because the host stream never runs dry mid-burst. seqhost mutant 16 catches it.

seqhost does not exercise mutants 15, 17 and 18 (one descriptor in the queue, row-aligned segments). The hnp bench covers them.

## SAFE-DESIGN checklist (before gate)

| # | Item | Status |
|---|------|--------|
| 1 | Pins | PASS. Same as s10: source-registered, with 2-stage `reset_landing`. |
| 2 | Reach | PASS. Same outline as s10, and every seam is a flop at the pin. |
| 3 | Fanout | Fixed for the three named nets: copies of `dq_rd` (about 24 loads per copy bit), `hr_v`/empty (32 per slice) and `u_cx` (about 21). The gate's mapped census must show 64 `dq_rdc`, 33 `hr_vc`, 33 `empty_c` and 128 `u_cx` `rbin_c` flops. Still open, the same class at about 550-600 loads: the wide-register load enables `u_ox.empty -> od/oa` (599), `u_sd.head_ready -> u_sd.h` (584), `-> s_hw_e` (583) and `fq_wr/p_wv -> fq` (547). These are flop-enable trees, not data cones. They are fixed if STA names them. |
| 4 | Depth | Fixed. The `st_row` / `st_left` ripple is now 4-bit plus registered 14-bit halves. The gate textbook must show the worst stage at 600 ps or less. |
| 5 | Storage | PASS. Same as s10. The added flops are 64 + 33 + 33 + 128 + about 150 counter-pipe bits, all far below 2 kb and none runtime-indexed. |
| 6 | Floorplan | Same as s10: 44% fill WARN-waived (macro and escape bound), macros on the lattice, aspect 1.56. |
| 7 | Clock | Same as s10: one `ck` root, no hard children, `io_hold_margin` 0.03. The gate must show spread of at most 80 ps at TT and FF. |
| 8 | Schedule | PASS. No edge is added (seqhost arrivals and hnp cycles are identical), so the HSH constant and MU-DIE-S81 are unchanged from s10 (HSH 8). |
