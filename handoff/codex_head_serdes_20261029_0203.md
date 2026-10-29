# CODEX HEAD SerDes / source entry handoff — explicit Claude reset

Parked on explicit ROOT reset notice. No jobs killed; no new jobs or merges after notice. Own worktrees clean; all source/receipt commits pushed. Parent HEAD owns integration. Do not mutate or kill the active old LEC.

## Branches and source

- `codex/head-serdes-ready-1029@e5014d81e`: thin natural existing `ot_s81_kp4_dchn` extraction, zero cycles; parent already merged. Source pins945, frame216x194.4um. Actual synth190283cells/21598um2. No six digital clones. Delta helper composes supplied physical descriptor into actual parent, never fabricates views.
- `codex/head-programme-1029@1f2412352`: actual source calendar, recovered fail-closed boot recipe, component entry gate + receipts; no RTL change. Last commit is independently cherry-pickable tile G1 review. Full source/main base a7168d188, but CTL RTL was byte-identical to b5c9faba0 before subsequent flag candidate.11 tests+5subtests pass. Compiler distinguishes explicit `reset_release` and `start_offset`, never substitutes new CA nominal+64 for delivered START.
- `codex/head-xb-flag-1029@f90fb1118`: fork of preceding programme branch. `d6adb68b8` is the one-file actual receiving RTL fix, directly cherry-pickable: existing rstop_xo uses XB bit20 as HEAD egress flag and index[19:13]=0..79; old CTL decoded[20:13] and rejected every flagged index128..207. Decode `{1'b0,ri_q[19:13]}` preserves low invalid80..127 rejection and adds0 cycles. `f90fb1118` tests flagged positive + invalid-low-index control through actual HOST/CTL/SRAM. Runtime active, not yet READY-qualified.
- `codex/head-dchn-count-1029@5d0139ac6`: based current-main b5c9faba0, shared RTL candidate `55ed628aa`, README a0d8ea3c9, exact runtime receipts5d0139ac6. Original actual CTS failure is ce1[9] mask -> nrc[5:1], worst -181.99ps. Candidate applies mask only to six-tail subtotal and carry-save reduces49 always-valid symbols; same nrc FF, no interface/reset/cycles changes. Frozen-original DCHN732-cycle/64frame comparison PASS; actual MUT2 division mutant caught64. Whole56-input combinational SAT timedout300s (rc124), UNPROVEN, not PASS/not contradiction. Algebra/row accounting explained in README. No physical improvement or mapped LEC claim, not adopted.
- Unadopted namespace alternatives remain `codex/head-hbc-namespace-candidate-1029@46eded2be`. DO NOT adopt wire bit528 or VARIABLE_WORDS160. Current minimal entry uses NO ordinary HFWD and legacy417 HOST book.

Local own WTs:
- `/srv/opentallas-scratch/claude/wt/codex-head-serdes` currently flag branch f90fb1118.
- `/srv/opentallas-scratch/claude/wt/codex-head-dchn-count` count branch5d0139ac6.
Remote equivalent WTs are intel2 `/srv/opentallas-scratch2/claude/wt/...`.

## Active jobs and exact checks

All heavy jobs were launched with ot-run. Keep running.

1. Original unchanged mapped Chien LEC: epyc2 container `hbmcore-ot_s81_kp4_dchn_head_-2780097`, unit `oth-ubuntu-2780044-1793257634`; original intel2 client1763703. Kit on epyc2 `/srv/opentallas-scratch2/claude/codex-head-serdes/kits4/ot_s81_kp4_dchn_head`. About108+min active98%CPU at last check, ~4.5GB. Hypothesis search, e.g. n_corr[18] rejected cut; no terminal failure. Check `ssh epyc2 'docker top hbmcore-ot_s81_kp4_dchn_head_-2780097 -eo pid,etime,time,pcpu,rss,comm'`; read kit `lec_run.log` / `lec/lec.json` when emitted. Main intel2 log `codex-head-serdes/place2.otrun.log`. Old synthesis and all source/config bytes match kit5. No ABC duplicate.
2. Diagnostic CTS/GRT on kit5, parent explicitly approved after independent actual G1. intel2 unit `oth-ubuntu-3990999-1793262751`, client3989584, container `codex-head-dchn-cts5`. Kit `/srv/opentallas-scratch2/claude/codex-head-serdes/kits5/ot_s81_kp4_dchn_head`; log parentdir`cts5.otrun.log`; scriptkit`diag_cts_grt.sh`. No detailedroute/abstract/signoff/release. CTS complete:226clock buffers,3227 real clock sinks, tap mean239ps/range224..251 vs250 target, checks PASS. TT setup repair failed closure -183.54->-181.99ps. FF reg2reg hold gate PASS0/0, port hold -36.18ps1endpoint. GRT routed180824nets/1889001um wire after591s; last log GRT setup repair says unable to repair all violations, FF hold repair next. Collect final per-corner gates/RC/setup/hold; don't treat insertion PASS as setup pass. Check `ssh intel2 'tail -n 30 /srv/opentallas-scratch2/claude/codex-head-serdes/cts5.otrun.log'`.
3. Actual flagged-XB entry gate active: intel2 unit `oth-ubuntu-1095981-1793264578`, client1095277, sourceWT flagf90fb1118. Output `/srv/opentallas-scratch2/claude/codex-head-entry/flag2`; mainlog`codex-head-serdes/flag2.otrun.log`. Uses existing real2safe8 peers/HOST/HBC/HOST276/CTL/4SRAMs. Modes0baseline,1wrongrank,2missing80thXB,3actualbit20flagpositive,4invalidlowindex80negative. Check verdict/run0..4/build logs. Compilation ongoing at park; no result yet.

Completed:
- Count exact job intel2 unit`oth-ubuntu-845443-1793263874`, client842108; output`codex-head-count/exact1`, mainlog`exact1.otrun.log`, exit1 solely SAT timeout124; bench0. Receipts tracked5d0139ac6.
- Read-only CTS paths unit`oth-ubuntu-713403-1793263498`, client712861, exit0; kit5`diag_cts_paths_tt.log`, `diag_cts_gate_tt.json`, mainlogparent`paths5.otrun.log`. Tracked as original_cts_* count receipts. All top5 actual critical paths lastchunkmask -> nrc bits, not GF inverse or reach.
- Original actual AR receiving entry unit`oth-ubuntu-3702200-1793261883` exit0; intel2`/srv/opentallas-scratch2/claude/codex-head-entry/entry1`; receipts programmebranch`results/head_provider_entry_codex_1029`.3HBC+8CSR including rank3CSR2+80actual1024-bitK_XB =160512halves/5120distinctfiniteBF16/81920bits. Checks all bits via256nativeSRAM replay records, START486 after actual residency, issue506. Wrongrank and missing80thXB controls CAUGHT. AR glen0, no MTP/fullHEAD G5/production transport claim. rbase97024/user513/position17/token7/programme9/dates are fixture inputs, not inferred production assignments. MTP requires explicit CSR5mtag.

## Actual G1 / preserved failures

- kit5 trial placement image actually viewed, compact uniform density; GRT50 overflow0, r2r232.36um, fill0.5039. GenericAUTO FAIL pin_unreg320 remains unchanged. Typed semantic INTERNAL_CORE943/943PASS.
- Independent actual typed review by tokens_hbm `ea1cb3c0a`:943signal ports,6440endpoint records,4369cone relations;132 x1->x2 FF resizes verified actual Liberty sequential/pin/clock interface. Fullcell/fullpin bound373.230um, actualfirst/lastFF237.030um <405. Receipt `results/head_serdes_reach_codex_1029/review.json`; copied kit5`typed_g1_review.json`. No generic rule waiver. Original autoFAIL preserved.
- Earlier gen1 sparse clock_family omission fixed; gen3 missing plan_pins postprocessor fixed; old strict face943checked545ok FAIL retained, not overwritten. Source exact732/mutant64 and preflight/source binding passed.

## Current production source/START gaps

Current portable351part plan/offsets from resize commit1fb78efd8 audited in programmebranch`current_contract_audit.json`: exact351coverage and351integer reset releases;351explicit null actualSTART offsets => compiler BLOCKED `ctl: missing actual START offset`, frames0. New CA n_nominal+rootsettle64 is NOT delivered START authority. Actual emittedSTART/fullnet proof remains resize owner. No owner decision required to invent dates.

TOK_DS now has current strictS13 HEAD source reference programme: intel1 `/srv/opentallas-scratch2/claude/codex-tok-s81-1028/cc_special_s13r_current/prog_HEAD_su` (`lowering.json`,`schedule.json`,`manifest.json`,`bound_data_links.json`,`prog/calendar.json`). Source WT intel1`/srv/opentallas-scratch2/claude/wt/codex-s81-frame-sub-1028` branchat5948fb8881.8ops:4PARTIAL hc_pre/norm +4GAP lm_head/argmax/merge/tokenreturn,98CTLrows. Existing rstop_xo egress80/80 is real source, but composed16sliceNX/rstd xfin16=234 is planningonly; crossdie publication dates/globaluser/token/HEADlowering absent. Current source reference calendarstage0/401HOSTwords is NOT receivingHEADstage81/417ABI. TOK_DS correcting stale partial diagnostic that incorrectly says consumer netlist absent. Flag20 mismatch above is concrete bridge bug, not owner permission.

Namespace: measured ordinary frame-valid HFWD magic payload collision is real in mux/HBC, but not activation (actual activation80XB). Actual CTL forwards512HFWD unchanged as K_HOST and LEP does not grammar-filter it; selected production producer grammar still unavailable. Minimal AR entry emits zeroordinaryHFWD and is not blocked by namespace. OWNER? already logged with correction in CODEX-LOG, no new decision adopted.

## Independent tile review performed on parent request

`1f2412352` is single independent reviewfile `results/geom_review/head_tile_independent_serdes_1029.json`, PASS-COND actualdata geometry. Viewed spnWT`results/head_tile_relays_1029/final_place.png`; actual0/27665captures>405,max400.95, comb0,DPL0,2440targets in legal macro corridors. Fresh reg_spine assignment required before diagnosticCTS; any data displacement must preserve4.05um margin. No oldclock/START age accepted.

Fresh clock image also personally viewed at spnWT`results/head_tile_clock_1029/clock_assignment.png` and planning_report.json:45taps/25749sinks,maxradius97.225um,maxstub365um;332BUFx4pads, residual25.84TT/20.71FF means planningonly. One unresolved visual check sent spn: HR0 plannednode(660,690) appears inside upper-right macro; clarify idealbranchpoint vs actual preserved/legalized h17BUFx24 centre. No unconditional clockG1 concurrence issued; parent/spn own continuation. No new heavy review run was started.

Final tile clock clarification from spn after park: HR0 planned site was moved
(660,690)->(660,717). Further physical pad rectangle audit found26 illegal
horizontal-left pad sites for IDs4/14/37/38/43. Clock G1 has NOT passed site
legality; no CTS launched. Source/results saved `ca2607c93` on
`codex/head-tile-relays-1029`, `results/head_tile_clock_1029/RESET_HANDOFF.md`.
The actual data reach remains unchanged and the independent data-only review
stays conditional. Parent informed; this supersedes the unresolved HR0 item.
