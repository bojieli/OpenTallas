# FAM-S81-COL handoff (started 11-20 23:4x PST, updated 11-21 00:5x)
Family: S81 col_h9_r0..r2 / col_h10_r0..r2 and all variants. Rep: col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f.
## State
- Lever 1 (COORD/FABLE-CLOSURE 23:45): +1 stage on ROM input buses at the pin face. Private proof chain running unattended:
  intel2 /srv/opentallas-scratch2/claude/fam-s81-col/chain.sh (log chain.log) = strict bind+LATCHECK (intel1 unit oth-ubuntu-2902890-1795248665, tree intel1 same dir src2, plan = J5 + 104 input rows + 12 ROM-PVAL output rows) -> kit_wave run-item (wave/spec.json) -> CTS tg_cts.sh -> posts OT_CTS_POST_TIMING (post-hook). Pass = TT setup >= -42, no ROM-face path in worst list.
- Delta on candC3c for J7 (UNPROVEN): epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-delta/delta_c3c.json (216 col types, 22,464 rows, gen_delta.py same dir). Goes to J7 unless proven before 11-21 13:00 PST.
- J5 a6 of the rep (intel1 ot-jobs col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-route-key-cardinal-3209518-1795232332) is in pregrt FF hold repair; post-hook TT -45.46 (after in-flow repair), FF hold -44.52 pre-repair. Do not touch.
- col_h9_r1 pv0bdbc3f3 (D8i a2) routed DRC 0 TT -274 FF -12: path read pending.
## Successor
Read chain.log; confirm or withdraw the J7 rows; then carry to siblings. Tools: run-item needs hub intel2; hardlink tree needs intel1 disk.
## 11-21 01:0x update (Fix A, COORD ruling)
- RD_EXTRA on main f9977af51c1 + 8a16e814dc5 (rtl/v41die/ot_s81_cfg7_seq.sv; bench modes rx1_* in tools/s81/fill2_cfg7_bench.sh). Bench: pr_pq1/pr_pq0/pr_bf and rx1_pq1/rx1_pq0/rx1_bf PASS, mutants pr_mut_prdl, rx1_mut_prdl, rx1_mut_tag FAIL. Masters take RD_EXTRA from +define+OT_S81_CFG7_RDX (default off).
- J7 rows: epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-delta/delta_c3c_rdx.json (216 types: ROM-input + q-bus rows, 30,108 total of which 7,644 q-bus) + manifest define OT_S81_CFG7_RDX. BLOCKER for J7: ot_s81_cfg7_seq is a HARD core (cores/views/ot_s81_cfg7_seq_signed_1101 lef/lib + views/ot_s81_cfg7_seq/source copy): RD_EXTRA=1 needs a re-hardened view (same pins) and a view-source update before the define can apply.
- Private proofs on J5 plan (col_h10_r0_p1 pvb095fa2f): A = input stages (intel2 chain fam-s81-col/chain.log), B = input + q-bus rows (fam-s81-col/v2/chain.log); the seq stays the signed J5 view, so B proves the physical closure only, not the RTL compensation.
## STAND-DOWN 11-21 00:55 PST (context 320k) - successor needed: FAM-S81-COL-R2 (Sonnet/Opus)
### Running (all unattended; do not restart)
- Proof A (ROM input stages only): intel1 unit oth-ubuntu-2902890-1795248665 = strict bind + LATCHECK, log intel1 /srv/opentallas-scratch2/claude/fam-s81-col/bind.log (was in RESET_ANCHOR). Hub chain intel2 PID 2144426 (fam-s81-col/chain.sh, log chain.log): bind -> kit_wave run-item wave/spec.json -> CTS tg_cts.sh -> posts OT_CTS_POST_TIMING (post-hook) under FAM-S81-COL, or posts the bind/kit failure.
- Proof B (inputs + q-bus rows = RD_EXTRA form): intel1 unit oth-ubuntu-3560521-1795250218, tree fam-s81-col/v2/src2, log v2/bind.log; hub chain intel2 PID 3711751 (v2/chain.sh, v2/chain.log), same stages, spec v2/wave/spec.json, event famcol2. The seq stays the signed J5 view, so B proves physical closure only.
- Rep: col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f on the J5 plan (plan_h2_2249.json sha 913a7026). Baseline J5 a6 post-hook TT -45.46 after repair (live, intel1 ot-jobs ...3209518-1795232332, in pregrt FF hold; do not touch). Pass = TT >= -42 and no ROM-face path in the worst list.
- Background poll (Bash run_in_background) on chain.log is armed in the dead session only; re-arm: ssh intel2 tail chain.log / v2/chain.log for CHAIN_DONE | BIND_FAIL | NO_PLACE.
### Deliverables on main / disk
- RD_EXTRA RTL: main f9977af51c1 + 8a16e814dc5; bench tools/s81/fill2_cfg7_bench.sh modes rx1_pq1/rx1_pq0/rx1_bf (PASS), pr_* (PASS), mutants FAIL. Define +define+OT_S81_CFG7_RDX turns it on for the masters ot_s81_cfg7_seq / _bf.
- J7 rows: epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-delta/delta_c3c_rdx.json (216 types, 30,108 sink D=1 rows = 22,464 ROM input + 7,644 q-bus; generator gen_delta.py there, run with FAM_NO_OUT=1). Unproven; goes to J7 only (J6 told). Needs manifest define OT_S81_CFG7_RDX and lanefix.py cycle declaration after the C3c/J7 bind (C3c bind still fails at stale dead-input defines).
- Lane clone intel1 /srv/opentallas-scratch2/claude/fam-s81-col/lane (branch fam-s81-col-rdx, pushed). Private plan generators fam-s81-col/mkplan.py (A), mkplan2.py (B); tool outputs trace_*.json, rd_report.json (relay_depth.py on J5 col_h9_r1: 105 read loops, 26 unfixed).
### COORD rulings 11-21
1. THIS LANE owns re-hardening ot_s81_cfg7_seq with RD_EXTRA=1: same pins and outline (no re-shape), new signed view, update views/ot_s81_cfg7_seq/source; plan then points the s* hard cores at the new view. This is the blocker for J7 (hard core ot_s81_cfg7_seq_signed_1101 is RD_EXTRA 0). NOT STARTED.
2. tok/s exact number: ask S81-J6-ASSEMBLY-R2 (owns the token compile / schedule tool) with the 1-cycle delay on lc->cfg/go_e/st/go_tag. Bound ~0 expected, 7% absolute worst.
3. Fix B (move c*_k within ~150 um of s*) only for pairs over 250 um (col_h9_r1: c8_5 351, c8_4 290; col_h10_r0_p1: c4_1 285, c4_0 282, c2_4 273, c2_0 273). Rows NOT written (cc_bank_rows.py-style legal-site generator needed).
### Open class findings (col_h9_r1 pv0bdbc3f3 D8i a2, TT -274)
ROM-face inputs 535 ends (worst -96.6; lever 1), t4.xai/t5.xbi lane-FIFO hop 68 ends (-274; RLYBR relay_depth rows missing in candC3c, derive with relay_depth.py once C3c binds), s*.q read loop 99 (-142.6; RD_EXTRA), bn6.e_r0 17 (-110; ROM-PVAL). col_h10_r0_p4 is -152 TT (hop/qbank class, J6 C3c).
### Successor steps
1. Read both chain.logs; post the post-hook TT for A and B; confirm/withdraw the J7 rows.
2. Re-harden the seq (RD_EXTRA=1, same pins/outline) via the core kit flow; sign the view; patch view-source; hand rows to S81-J6-ASSEMBLY-R2 for J7.
3. Ask J6-R2 for the tok/s number.
4. Fix B rows for the >250 um pairs; then carry the proven fix to the 120 types without a J5 kit.
## 11-21 01:3x UPDATE (after stand-down)
- Proof A: strict bind + LATCHECK PASSED (09:28 UTC, tree intel1 fam-s81-col/src2, bind out fam-s81-col/bind). kit_wave run-item then FAILED at stage src_manifest (rc 1, KW_STAGE_RC src_manifest 1; hub fam-s81-col/wave/run_item.log): the tool now requires build tree = git archive of a main sha + listed overlay files (sha256 checked) and rejects hardlinked writable trees (class 4/5 rule). Fix for the successor: put the J5 plan + RD/ROM rows in as an overlay on a git-archive tree (spec fields src_manifest / src_manifest_hash / src_overlay), or run the kit steps by hand (bind.py kit-rtl, gen.py phys, run_kit.sh place, tg_cts.sh) from the bind out. No CTS read exists yet.
- Proof B (v2) will hit the same src_manifest refusal when its bind ends; chain v2/chain.log.
