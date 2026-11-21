# QC-PLAN-R9 handoff (started 2026-11-21 03:4x PST; succeeds QC-PLAN-R8). Read QC-PLAN-R8.md RESUME + b13 sections first.

## 03:5x state
- b12 (929928f3c22a) ended BIND_RC 1 with R8_STALE 30 only (refresh path bug). R8 relaunched b13 before standing down:
  epyc8 unit oth-ubuntu-3618703-1795261366, inputs v2b_host/in13/ (plan = b12 plan 929928f3c22a), bind_b13.sh (RR = rt/7ff721a00978 r8_refresh.py).
- NOTE: R9 launched a duplicate b13 at 11:43 UTC that failed at `test ! -e b13` (no harm to R8's run) BUT its redirect truncated
  v2b_host/b13.out. Read results from v2b_host/b13/{bind.log,bind/bind_report.json,latcheck.json}, not b13.out.
  The R9 debug bind (b13dbg) was cancelled. bind_b13.sh was rewritten with identical content (diff vs R8's open fd: none).
- R9 post-bind chain on b13: epyc8 v2b_host/chain2_b13.sh (pid 3673554, log chain2_b13.log): ot-wait R8 unit -> gate bind errors 0 + latcheck.json
  -> G0 (check.py) + event_census (event s29q103S4Q9N46R6V2b13) -> 7 proof GENs (watch_b12 type list) into b13/post_bind + b13/proof_gen.
- b14 (parallel candidate) = b12 plan + 12 zero-cycle HC/ST ft sites from Codex v2b/hcst_ft_followup (SITED, hops <= 300 um, stations unchanged):
  9x b_hw_ctl_hc3 (sle/slw st_b v1/v2) + 3x cws3 (sle_st_b_v2). Plan epyc8 /srv/opentallas-scratch2/claude/qc-plan-r9/b14in/b14_plan.json c3f5b1eb9c1e
  (compose_b14.py). Chain qc-plan-r9/chain_b14.sh (pid 3729568, log chain_b14.log, bind log b14.out): bind -> G0 + census -> proof GEN sle_st_b_v2__clfde1249e.
  Choice: if b14 binds clean + G0 PASS, apply b14 (b13 proofs cover all other types; st_b proof from b14); else apply b13 and carry the 12 to V3.
- FEFW item (13 C-plan types without regs_um): 36 slots/19 types already sited in b10+ (hcst_ft/ledger.json accepted); 12 more in b14;
  12 remaining are ENDPOINT_REACH (9 x_fw_ctl_p2 need >= 3 hops, 3 x_su_l0_ctl need >= 4) = cycle reprice at tree joins -> V3 (risk of PARAM_REGEN imbalance).
## Next
- On bind PASS: G0 + census read, proof kits to GRT (die priority, CTS post-hook), geometry to GEOM-REVIEW, then pack (pack_b12.py pattern) / seal / apply.
- On apply: release 11 cb hold_items (65f9eaf04c5, 8cd505347e7) + 3 fe (76a934188b0/56a3cbdebf0/678d61ae6c4) + cbn_q00__cldbcda913 via kit_wave_edit.
- Re-sign: add 6 N_PAD siblings after the 6 reps sign. Lockup rows held (LOCKUP-STATION-R3). FAM-QC-COLL ODPRE rows staged (not proven to GRT) -> V3.

## 04:4x state (supersedes 03:5x "Choice")
- b13 (R8 unit) + b14 (R9) both strict RC 1 with the SAME 3 errors after a working R8 refresh (6 west dvs rs_s members 24->25):
  TYPE_SPLIT sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa (E3 xhead3 N_PAD 3 S_PAD 1 vs E4 N_PAD 3), TYPE_SPLIT slw_hc0__cl4f54b7a3
  (W0 N_PAD 3 vs W1-W5 N_PAD 3 S_PAD 1), EMIT clock landing (follows the splits). QFT/PARAM_REGEN/hard-core clean. b14's 12 ft sites add no error.
- Fix = R6 V1 pattern: non-strict bind (nsbind.sh) -> param_class_split.py (plan + sidecar) -> strict bind with PCS_REPORT (clones replace base in
  asbuilt internal_stations_types; bind_b15.sh = bind_b13.sh + that step). +2 types (one clone per new value set) to sign.
- LIVE: epyc8 /srv/opentallas-scratch2/claude/qc-plan-r9/chain_b15.sh (pid 67275, log chain_b15.log): nsbind b14 -> pcs (b15in/) -> strict b15
  (b15.out) -> G0 + census (event s29q103S4Q9N46R6V2b15) -> 7 proof GENs (b15/post_bind, b15/proof_gen). b13/b14 chains ended (no G0).
- 05:0x: first chain_b15 stopped: the non-strict bind also stops on EMIT, so no bound top for param_class_split. Wrapper qc-plan-r9/pcs_from_typesplit.py feeds bind_report.type_splits groups to the tool (same clone_name/apply_plan/apply_side). Check: sle_hc0..pv1c2f9baa -> __pv6e886d59 (E3) + __pv48712631 (E4); slw_hc0__cl4f54b7a3 -> __pvde134a90 (W0,W4) + __pvd0aa3ddc (W1,W3,W5). LIVE chain_b15b.sh pid 428301 (log chain_b15b.log).
- 05:0x FABLE-PD-QC-0440 response (posted): V2 = b15 as is. (a) >405 rows, (b) 212 slots 301-400, (c) tap rows + core-tap insertion rows, (e) cb inst_taps after the FAM-QC-CB fp4 proof, and cbf_q01/_s2 reset rows -> V3 (11-22). (d) leaf-leg checker: helper agent QC-PLAN-R9-LEAFLEG (tools/precheck/reset_leaf_legs.py, advisory) running from rtx-pro. Revised V2 ETA: G0 ~06:30, GENs ~07:00, proofs to GRT ~12-14, apply ~15:00.
- 05:1x: RESET-RELAY-GEN-R3 out2 rows: cbf_q01 + cbf_q01_s2 reset.inst_taps (4 each, 0 cycles; reset sections otherwise identical to V2) -> b16 = b15 plan + those rows, chain qc-plan-r9/chain_b16.sh (pid 598908, log chain_b16.log, bind b16.out), proof GEN cbf_q01. Apply b16 if it binds clean + G0, else b15 and the rows go to V3. cbn_q11__cl5cc92dfe local tap: already in V2 (reset.local_taps_um [[1015.2, 2497.365]], FAM-QC-CB row) - no new row. NOTE chain_b15b.log is empty (stdout went to /dev/null by mistake): read b15.out + b15/post_bind/*.
