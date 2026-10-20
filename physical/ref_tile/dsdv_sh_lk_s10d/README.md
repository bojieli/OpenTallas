# dsdv_sh_lk_s10d: s10c + kept enable-tree copies (S81-SHLK10, LEAD3-S81, 2026-10-19)

s10d is the PARALLEL FALLBACK route of dsdv_sh_lk_s10c (coordinator-approved, fe1c70f78): the same floorplan, macros,
pins, clock and s10c RTL, plus `OT_S81_SH_S10D`, which replaces the four ~560-600-load flop-enable trees that the s10c
gate textbook named (`_064395_` OR3 597, `_065354_` OR2 586, `_066042_`/`_065313_` NAND2 584/583, four OR3 558) with
KEPT register copies. Same values on the same edges; no edge added (HSH 8, MU-DIE-S81 pricing unchanged).

## s10d changes (`OT_S81_SH_S10D`; every copy is a `(* keep *)` reg, checked in the gate PREOPT netlist 1_2_yosys.v)

| tree (s10c) | where | s10d |
|---|---|---|
| ox_pop -> o_we/o_addr/o_d (289 flops), OR3 597 | rtl/hdc/ingest/ot_rom_host_ingest.sv die face | 10 copies `ocr_nz_c` / `pace_c` (registered NEXT-state ocr != 0 / pace_ok) + 10 `u_ox.empty_c` (EC 10); `ox_pop_c[k]` = AND3 of copy k enables one 29-bit payload slice |
| sd_pop -> h_q (289 flops), OR2 586 | rtl/dsrom_sys/s81_dv/unit/dsdv_sh_sd.sv | h_q captures mem_q on every edge (it is read only on the edge after a pop, when it equals the popped word as before) |
| pop_q && dst[s] -> hw payload (291 flops / stack), NAND2 584/583 | dsdv_sh_sd.sv | 10 copies `popq_c` + 10 copies `hk_c` = {hwe, ha, hd[65:64]} of mem_q; copy g decodes its own dst for one 30-bit slice |
| p_wv && fq_wr == e -> fq[e] (288 flops), 4 x OR3 558 | rtl/hdc/ingest/ot_hdc_kv_ingest.sv g_sp | 9 copies `p_wv_c` + 9 one-hot write-pointer copies `fq_wh` (32 b each); `fq_nz` = registered fq_n != 0 (pop / sp_acc enable; the s10c GRT worst endpoint was sp_acc[31] -40.5 ps @770) |

Simulation guards (`ifndef SYNTHESIS`): every copy is checked against its master each cycle ($fatal on divergence).
Mutants: hnp s10dox10 `OT_S81_SH_MUT_S10DOX` (ox payload enable copy 2 stuck 0; seqhost 22 builds but its stream leaves
o_d bits 58..86 constant, so it is not exercised there), seqhost 23 `OT_S81_SH_MUT_S10DHW` (svc payload
copy 4 decodes we 0), 24 `OT_ING_MUT_S10DFQ` (fq write-pointer copy 5 stalls; also hnp s10dfq10). Seqhost 14
(HQSTALE) has an s10d form (pop-edge emit). Witnesses: results/rtl/s81_shlk_s10d_1019.

---

# (inherited) dsdv_sh_lk_s10c: congestion-safe sh_lk (S81-SHLK/SHLK, LEAD2-S81, 2026-10-19)

s10c combines three things:

- the s10w floorplan: 345.6 x 194.4, four right-sized masters at x 43.2 / 216.0 and y 43.2 / 129.6, with a 73.7-um centre channel;
- the s10b RTL: kept `dq_rd`, `hr_v`, empty and `u_cx` copies, plus split `st_row` / `st_left`;
- two new depth fixes under `OT_S81_SH_S10C`.

It adds no edge.

## Why (gate facts, all `--cts --remote auto`)

| kit | floorplan | verdict | GRT overflow | spread TT/FF ps | placement reg->reg | textbook worst stage |
|-----|-----------|---------|--------------|-----------------|--------------------|----------------------|
| s10 (40261329f) | 302.4 wide, 30.5-um channel | FAIL | 146 (M4, channel x~130) | 65.8 / 59.3 | -35.2 (sp_iss[30]) | st_row->s_grp 690 ps / 19 lv |
| s10w (40261329f) | 345.6 wide, 73.7-um channel | WARN, 0 fail | 0 | 46.7 / 42.2 | -52.7 (sp_iss[30]) | st_row->s_grp 690 ps / 19 lv |
| s10b (3ebb699a9) | 302.4 wide, 30.5-um channel | FAIL | 4 (M4, x~131) | 96.0 / 86.6 FAIL | -88.3 (sp_iss[29]) | st_ph->p_wa 810 ps / 23 lv |

The 30.5-um channel is the congestion: both s10 and s10b overflow there, and s10w does not. s10b removed the s_grp stage. The remaining worst endpoints are the stream address (`st_ph`/`st_mode` mux, then a 32-b add, then `p_wa`) and the completion issue counter (`st_go && st_wv` enable cone, then a 32-b increment, then `sp_iss`).

## Changes (`OT_S81_SH_S10C`, rtl/hdc/ingest/ot_hdc_kv_ingest.sv; no edge added)

1. **Stream address.** Stage P registers base `p_wb` (st_d[47:16] / u_raddr / u_kcode / u_kscal) and offset `p_wo` (st_row / st_sec / st_ph / ph==4). Both are muxed by mode and phase, with no adder. Stage O computes `p_wa = p_wb + p_wo`, in parallel with the 8:1 head-byte select and before the FIFO write. The value and the edge are the same as s10b's `p_wa <= st_wa`.
2. **Issue counter.** `sp_iss` counts the registered `p_wv`, which is `st_go && st_wv` one edge later, so the enable is a flop. After edge t+1, `sp_iss` equals the s10b count after edge t. So `dq_c2 <= sp_iss` gives exactly s10b's `dq_c1 -> dq_c2` value on the same edge.

Mutants (fail witnesses in results/rtl/s81_shlk_s10c_1019):

- hnp s10cwa10 (seqhost 20 builds but is not exercised by the seqhost stream), `OT_ING_MUT_S10CWA`: computes base | offset instead of the sum.
- hnp s10ciss10 (seqhost 21 likewise not exercised), `OT_ING_MUT_S10CISS`: the registered issue counter also counts the IKEY scale-capture step (`p_sc`), so done counts run high. A first mutant that routed the late count through `dq_c1` was missed by hnp: no done lands on the edge right after an issue. It was dropped as unobservable at the boundary.

## SAFE-DESIGN checklist

| # | Item | Status |
|---|------|--------|
| 1 | Pins | PASS. Source-registered: every input lands in a flop and every output is a flop. Eight input bits (f_ks[52], kd_i[53], j_i[32], s_jd_w/e, f_host[0]) pass one AND with the local registered `rn` before the flop. That is a reset-valid gate, not a cone. reset_landing has 2 stages and 8 rst_n copies, max 32 loads per copy. |
| 2 | Reach | Waived-with-reason. The outline is 345.6 x 194.4, so a corner-to-corner Manhattan distance is at most 540 um. The Codex s10w native model counted 351 FF root/sink pairs over 405 um (max 519 um), all FF roots. Inside a registered hop, the route inserts repeaters. Acceptance is TT/FF STA at 833 ps, not a geometric bound. |
| 3 | Fanout | s10b fixed dq_rd 794, hr_d enable 890, u_cx rbin 679. **s10d FIXED** the remaining ~560-600-load enable trees (ox_pop, sd_pop, pop_q&&dst, p_wv&&fq_wr) with kept register copies (<=32 flops per copy); copy counts verified in the gate PREOPT netlist. |
| 4 | Depth | Fixed. The st_row ripple was fixed in s10b. This kit fixes st_ph->p_wa (810 ps / 23 lv) and sp_iss. The gate textbook must show 600 ps or less, or a TT reg->reg of 0 or better. |
| 5 | Storage | PASS. Host/req/svc FIFOs live in four SRAM masters (2 x 16x257 + 2 x 16x289). The realigner (8 x 256) is one 2048-b pair window at the 2 kb threshold. The other queues are 4-16 entries. |
| 6 | Floorplan | Macros sit on the 43.2 lattice. The centre channel is 73.7 um, and s10w measured GRT 0 there. Aspect is 1.78. Fill is 37-38% (std density 21%). This is WARN-waived: the outline is set by macros and pins, with 99% face pin demand at 1207 pins on N (3.5/um). |
| 7 | Clock | One `ck` root, no hard children, io_hold_margin 0.03. s10w on the same floorplan measured TT 46.7 / FF 42.2 ps. The gate must show 80 ps or less. |
| 8 | Schedule | PASS. No edge is added (same values and edges as s10b), so HSH stays 8 and the MU-DIE-S81 pricing is unchanged. |
