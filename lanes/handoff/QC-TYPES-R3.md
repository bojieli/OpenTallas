# QC-TYPES-R3 handoff (11-17)
- xj (attempt_xj, E8 qc-types-r/xj_cts_1117): 3/5 old ends MET (+332..+373), tap_d[431] -70.0 / [442] -73.5 FAIL (first QN->buffer hop ~245 ps). 92->22 stretched hops (Codex count). COORD approval pending; not approved.
- Token DS capture-only 63bd74e1c7: already committed/pushed/gated/COORD APPROVED by TOKEN-R. Nothing to do.
- Face-row pilot (loved-redfish qc-collucie-1117, hold_paths/hold_paths.log:491-577): internal FF -28.008 = u_cland_shr_p_tx_i ring dch[4].u_dsel/y[25] (clk_t9, latch 163 ps) -> INV -> u_bin_shr_p_tx_i/q[281] (clk_t6, capture 201 ps), 0 logic, 38 ps capture-late + 25 ps uncertainty. Fix: HB4 at the capture pin (HOLD-FLOW-R internal ECO). Not launched.
- TODO: cbn_q01 routed setup + R-MINIMAL (pilot only post-CTS), 18-type wave with latch_except row, face-row hold ECO.
