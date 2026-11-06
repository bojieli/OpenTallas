QC-CBN-RF1 / RING-SPLIT-1106 — CBN safe form B, ring part (candidate plan event, NOT applied to plan_qc52)

Types: cbn_q00__cl622f65d2 (GRT-0116 overflow 1,170,056) and cbn_q00__cldbcda913 (FF hold -395.43 ps / 12014 ep).

ESTIMATE (measured on the failing kits)
- GRT (cl622 attempt_7, epyc4 qc-wave-1105f2): overflow M6 688,144 + M4 453,012, horizontal; 15,716 of 17,641 sampled
  boxes have capacity 0 (over the 4 NK macros, OBS M1-M7). Ring nets = 39.5k of ~70k sampled overflow net hits
  (rsf_i 28.2k, na_i00 11.3k); hot spot x 0-200 / y 2300-2500. Cause: plan bands put na_i00 / rsf_i rings
  (11,606 cells each) in the 82-um left strip, far below their north-face pins.
  -> hardening the rings directly under their pins removes the main overflow source. Residual (r8b/lpad/d10 chains)
     NOT proved: needs the parent vB GRT.
- HOLD (cldb attempt_6, epyc5 codex-wave-1105): all 12014 failing paths are clk->clk ZERO-LOGIC shift chains
  across grid taps (u_d*_u_t_*_n_y r[0]->r[1] -395, u_r8b_strap_r8pad_* -383, fab a_d -233, lpad_nb -220,
  ft_rsf_o stations -88, 515 ring->ft_rsf_o -183). Not CDC (not QC-HOLDCLS-1's class), not ring-internal.
  Mechanism: 160 ps SDC tap window (no CRPR across taps) + ~243 ps tap insertion imbalance (clk_t26 regs ~140 ps vs
  clk_t25 383 ps, long port wire, slew 102-143). cl622 has the same chains (pre-repair -356 / 10,204).
  -> ring hardening does NOT fix hold. Parent vB also needs a hold-safe chain form (tap-local chains / HB4 or lockup
     latch per OWNER 10-27 rule / balanced taps) before it can pass the FF hold gate.

EVENT (delta_cbn_ring_split_1106.py plan_qc52.json -> plan_cbn_geometry.json, 0 added cycles)
  plan_qc52.json sha256 b398e285557293311294917c275d0db0890e79d33008588f95e9c4e4ce24125f
  plan_cbn_geometry.json sha256 25e035f66d20b2b655a33b941aaf0772c356b0413c63a63496a52f74a34f1d36 (not committed,
  17 MB; regenerate with the delta, ~10 min for the reset-tree re-solve)
  5 hard rings per type (identical in both types), all registered faces (ot_dp_clk_landing_cas WREG/DSREP):
    na_i00 cl_na_i00  sle_cland_w515_n     (REUSE, AP-signed HC0 view, pin table sha 37dc78.. byte-identical)
    rsf_i  cl_rsf_i   sle_cland_w515_n_300 (new: pin order differs from w515_n in 359 positions)
    nb_i00 cl_nb_i00  sle_cland_w515_n_301 (new: 514 positions differ)
    bc_i00 cl_bc_i00  sle_cland_w517_s_300 (new)
    bc_i10 cl_bc_i10  sle_cland_w517_s_301 (new; bit order differs from bc_i00 -> Codex draft's shared W517S wrong)
  North rings y 2466.72 (88.56 x 51.84), south rings y 17.28 (89.184 x 51.84); non-overlap/outline asserted, soft
  monitor bands untouched. Soft cells 172,914 -> ~114,838 (<=150k). Reset collector tree re-solved: depth 10 -> 10.
  Core taps: reused master at its signed 90.19/72.02 ps; new masters at the 250/202.5 target (re-measure from kits).
  GEOM: cbn_ring_geometry.png (render.py).
PROOF: proof/<master>/ iverilog lock-step 500 edges wrapper vs ot_dp_clk_landing_cas: bad=0; mutant q^1: bad=480.
  proof/main_vs_kit_rtl: main rtl/common (bfc3c3.., opt-in SLOT_LAP/FREG off) vs failing-kit RTL (94b478..)
  lock-step W515/W517 bad=0, mutant bad=480.
KITS: kits_recipes.json; epyc5 /srv/opentallas-scratch3/claude/qc-cbn-rf1/kits/<master>_hcbn1106, ot-run finish 8G/4T.
NEXT: parent <class>_vB kits after (1) the 4 child kits sign off and (2) a hold-safe chain form is chosen.
