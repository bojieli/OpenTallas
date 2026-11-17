# QC-TYPES-R — CODEX takeover 2026-11-16 19:5x PST

Direct existing lane continuation; no engine RTL or plan edits.

## Completed
- headseg44 hf E7 `fable-fix-qc-cbglue/headseg44/runs_hf/headseg44_kv1/final_nominal833/signoff`: canonical R-MINIMAL SIGNED, TT +133.23ps, DRC0/antenna0, exhaustive internal FF0 violations (global -94.9 is773 port-start paths). Actual LEC still CPU-active. Export BOTH archives + locked INDEX COMPLETE coord3fd3e9a7f699; component key qwen_compute/qfd_su_mem44_seg8_kv1; ODBsha fcb69580eba9770263b661f0546d364d4d0f221deab8c0426bf1b147525c5382,105063116bytes. No generic view registration.
- Four tail1 param masters already SIGNED/exported; do not rerun redundant H16/H17 masters.

## Running
- W0: E2 `/srv/opentallas-scratch2/claude/qc-types-r/w0_hold858`, existing 858 HB4 route active (DRT iteration1 progressing, initial478 violations ->286@50pct). No job changed. `final_after_route.sh` STAGED not yet launched: verifies terminal marker + empty DRC, exports held ODB netlist/DEF, same canonical 833/0/25 TT250/FF202.5 frame, fresh RCX signoff. Launch via ot-run40GB8threads only after route completes.
- W1 distinct248-output full-five-leaf form: E2 `qc-types-r/w1_hf_1116`, floorplan-only admitted unit oth-ubuntu-4167269-1794887316, client tool session36042. Source original44868 retained; new private cp-a source overlays approved main12fbf47634 orfs_hold_mm.py/tcl + reg2reg10/HB4/signoff-RC parity; engineRTL unchanged,0cycles. Personally LOOKED original planned8macros/>20umchannels/openwestband image PASS-COND; review prelaunch_review.json. NEXT actual floorplan render+LOOK then ordinary make continuation without resynthesis.
- coll_n original hold80 already minimal SIGNED/exported. Advisory LEC2 failed TAPCELL unknown; LEC3 physical TAP-only export failed DECAP unknown (preserved). LEC4 active E2 qc-pinaccess-o/coll_n_hold80_1116 unit oth-ubuntu-4123742-1794887165, client tool session2319, `lec4.run.log`. New logical4 export removes ONLY zero-connected-pin TAPCELL/DECAP/FILLER instances; all other netlist text unchanged, physicalODB untouched. Receipt lec_physical_export4.json. Python preprocessing CPU100pct observed; preserve.
- P3 m10 E10 fable-fix-qc-hcfe/p3_fault_split_e1_margin10_1116 still native hold repair iteration0,6negative/-24.28574 but6213below+10; preserve progressing admitted job, no duplicate. Predecessor20ps stopped by exactunit earlier. If terminal failure: internal-only six-endpoint HB4 plan, not another global margin chase.

## Failure ownership
- cbx_q10 cl89936551 -1803 / cl94a12200_h -1928: oldS4Q6D source lacks r301 xcst_rep, exact prior xstation fanout class. Next fresh L2 proof must carry r301, not retry oldinputs.
- cbn_q01 clab6e67f2 cee3540cfd65: actual old kit hold21467ep/21431cross-tap, worstDLATCH_N u_lk_nk_u_t_0_2_tap -211.66. Guard45 inserted36093buffers with no worstgain, fell back unchangedCTS,450GRTiterations hit obsolete12h cap. DISTINCT forwarded-ring/latch hold class; r301 alone not proof. Kf is FE-only, so retain existing clock52 hold through Kf; next L2 clock-row proof must include targeted latch endpoint read. Parent QC-PLAN-R handles held types.

No owner question. No fresh Fable review claimed.
