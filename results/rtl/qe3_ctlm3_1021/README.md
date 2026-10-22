# QE3-CTLM3 10-21 -- Q.STA.TTC.4 CTLM RTL timing successor (lp9f, CALREG 15) + kits safe14a / safe14b

## Why (safe12c post-CTS, classified)
`safe12c_cts_classes.txt` (own STA of EP9 `qfd_tt_ctlm_dv_safe12c-20261021-131509` 4_1_cts.odb + signoff.sdc, propagated
clocks, placement RC; instance -> RTL source via the lp9d generic `u_<i>` order; script `safe12c_cts_paths.tcl`):
4171 failing endpoints.
- A (-897 ps, ~2400 eps): OPSEG leaf op register (qfd_sys_face_mu_dhuser_p:217) -> u_start / u_user -> cal_mu go_user ->
  go_u / frz_u -> hgo -> isel / i_any -> issue kind decode -> issue fault flags (37 levels), and the same start into every
  playhead enable (selectors, read-valid copies, fq_wd, pst, ROM request).
- B (-780 / -598, ~200 eps): per-user FIFO SRAM u_fifo rd_out (441 ps access, macro clock ~140 ps late) -> 4:1 word select
  -> FIREDQ candidate KS adders -> dq / fire_q.
- C (-721 OT entries / -259 propagated): u_hr native_tok -> 600 um unregistered output.
- smaller: pw observer -> program_obs -579 (75 eps), u_lpl_7_r internal -315, tl outputs -306.

## What (rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv `CALREG`, parents pass it; default 0 = previous RTL)
- [0] FQREG: per-playhead ring = 2 x 512 flops (1 kb, under the 2 kb SRAM rule) written at the arrival edge + registered
  next head `nx_q`; a pop loads the head from `nx_q`, the FIREDQ candidates read a register; ring -> nx is flop -> 8:1
  one-hot AND-OR (kept selector copies) -> flop.  The 4 FIFO SRAM macros are gone.  Edge-identical: calr_port lockstep vs
  the f16 reference 0 mismatched edges of 1,059,923 (CALREG 1 and 5), mutants 34 / 2 still FAIL; T_0 rule unchanged.
- [1] STARTREG: start pins + their decode (user one-hot, range check, stage class / bound) registered in front of the
  playheads (+1 edge start -> issue); u_gi delays the face start's head / ME / F16-witness consumers by the same edge
  (h_start / h_stage / h_tok / h_pos, w_start), so head, ME station and calendar keep their relative timing.
- [2] ISSUEFLAT: issue enables and issue fault sites per playhead from the registered head; isel only selects (exact).
- [3] NOUTREG (u_thru): native_tok / native_pos / layer_context_v output registers beside u_hr (+1 edge on the three).

## Price (cycle ledger; cycles accepted by owner)
- +1 edge from every segment start (face dh start, OPSEG leaf start) to its calendar issue / head start / ME start;
  T_k inside a segment and the calr10 image are unchanged (no re-pack: FQREG keeps T_0 >= 5 + (NU - 1) = 8).
  Token path: <= +38 edges / token (one per layer segment incl. stage 0 and 37) of ~38 x 6,886 = 0.015 %.
  Measured: calr_rel TABLE_REL latency 9 -> 10 (unit), token bench TLOAD latency 11 -> 12 (flat == netlist).
- +1 edge on native_tok / native_pos / layer_context_v (port_latency.json records it after the first route).
- area: mapped std 12,509 -> 13,141 um2 (+5 %), 4 SRAM macros removed (-105,454 um2 hard area).

## Netlist chain (run11.sh = QW-TLPROD run10.sh recipe on ot-epyc6 with `-set CALREG 15`)
generic -> construct_parent7 -> `rtl/qwen_dv/lp9f_np` (native census PASS max 32, textbook depth 718.5/24 -> 675.1/21 ps/lv,
reg_to_out 3 -> 0 levels, ck_core ff 11,928 -> 14,012, macro pins 12 -> 8) -> `tools/qwen_dv/npl_rename.py` (lp9d_np ->
lp9d_npl hand transform as a tool; reproduces the committed lp9d_npl byte-exact) -> replica_role_split -> `rtl/qwen_dv/lp9f_rr`
(43 groups, 2981 pins, +15 copies; rr_equiv 0 non-identical drivers; one census fix recorded in the rr record: u_qkorr_14.X
moved to the identical logic-only copy, mapped census r1 PASS max 32).

## Benches (existing only, Verilator 5.050, witness/)
- calr_port (unit lockstep vs f16 ref): CALREG 1 / 5 / 0 PASS 0 mismatched edges; mut 34 / 2 FAIL.
- calr_rel (TABLE_REL unit, CALREG 15): m0 PASS 144 loads; m35 / none / abs1 FAIL.
- bench10 (tb_np10 + `.CALREG(15)` on the flat side; flat RTL vs lp9f_np landed netlist lockstep): rnd_mut0 PASS, mut1/2 FAIL;
  calr_mut0 PASS, rommut FAIL; tok_rel / tok_rel_rnd PASS (TLOAD_PRODUCER PASS, 36 loads both sides); norel / abs1 / drop17
  FAIL as expected.  BENCH10_RC 0.
- rtl/test/mu_qwen_seq run_mu_seq.sh: does not build at HEAD (its SOURCES list lacks ot_ks_add / the PW observer that
  qfd_dv_cmd_cal_mu has needed since CTLM7) -- pre-existing, not run.
