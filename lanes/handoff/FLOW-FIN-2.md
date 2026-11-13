# FLOW-FIN-2 handoff (Opus successor of RULES-FLOW-1; R-FLOW goes back to RULES-FLOW-1)

## 2026-11-13 07:27 PST handback
State: RULEBOOK R-FLOW section NOT edited by me (HOLDTAP-FIN-2 had uncommitted R-CLOCK edits in the same file in the shared
~/coord tree; coord-commit.sh stages the whole file, so I held my edit). No READY posted. No job cancelled or relaunched.

### Branch
- epyc7 /srv/opentallas-scratch2/claude/rules-flow-1/wt, branch claude/rules-flow-1-1113 = 15693dff8a (1 commit), rebased
  cleanly onto origin/main 99b30dde2a (contains 24b08535da; no upstream change to any file the commit touches).
  Was aa1d118875 on 055e36edab. NOT pushed. Untracked tools/die_plan/vclk_measured_band.json in the wt is not ours; left alone.
- Commit still has GPL_KEEP_OVERFLOW 0.25 in gen_phys.RFLOW (R-FLOW-7 undecided, see below).

### Tests on 15693dff8a
- Focused: test_rflow_defaults, test_place_fanout_cap, autopilot/test_gp_noconverge_gate, post_route_drv/test_prd_margins:
  39 passed + 2 subtests.
- Per-file (perfile.sh, 297 files, one pytest per file): default rflow/pf_fin2, OT_RFLOW=0 rflow/pf_fin2off (summary.txt).
  Same 13 files fail in both = pre-existing on main (checkpoint_cleanup, flow_gen_1028, flow_hold_basis, fresh_kit,
  gen_phys_bump_ports, grt183_kit, kit_cts_hook, legacy_gate, master_plan_r3, partition_clock_binding, post_route_drv,
  tap_chain_affinity collection error, timing_libs). Default run also had test_watchdog
  test_verify_cpu_sample_counts_busy_process (0.97 < 1.0 s CPU at load 140): flake, passes 2/2 on rerun, no R-FLOW reference.
  => R-FLOW adds no test failure.

### A/B so far (all DRC 0; `python3 -I ab/abrow.py <kitdir>` in epyc7 rules-flow-1/ab)
| arm | TT slew pins | TT setup | FF hold | cells | note |
|---|---|---|---|---|---|
| HEAD hd_turn_b old (turn_b_old) | 1,408 (424 ps) | +100.36 | -26.35 / 47 | 31,190 | |
| HEAD hd_turn_b R-FLOW + keep (turn_b_v2) | 0 | +100.52 | -24.27 / 32 | 31,453 | budget 3.69 % OK |
| HEAD hd_turn_b R-FLOW no keep (tb_E_nokeep) | 0 | +99.02 | -16.72 / 27 | 31,452 | budget 3.63 % OK |
| S81 t21 old (t21_old) | 135 (425 ps) | +165.85 | -17.34 / 409 | 212,282 | kit max wire 50 (relay_bay) |
| S81 t21 R-FLOW + keep (t21) | 0 | +122.10 | -8.62 / 76 | 214,945 (+1.3 %, area +5.7 %) | budget 2.42 % OK; max wire 50 both arms |
| KV kv3_sys_SD_v1 RA=0 only (kv_ra0) | 1,037 (440 ps) | -15.04 / 4 | -13.43 / 269 | 84,462 | DRT-0255 gone, route completes |
| KV kv3_sys_SD_v1 RA=0 + R-FLOW (kv_rflow) | 0 | +42.65 | -20.54 / 540 | 87,419 (+3.5 %, WL +5.9 %) | budget 1.74 % OK |
Readings: R-FLOW-6 proven on KV (RA=0 alone removes DRT-0255 on an M8-grant kit; hd_tile stays HEAD-97/structural). R-FLOW-1/2
clear slew on HEAD, S81, KV. Remaining failures are hold (R-CLOCK class; KV hold endpoints rise 269 -> 540, not masked by a
setting) and t21 setup loses 44 ps but stays +122. t21 FF hold -8.62 / 76 is inside the late-ECO window.

### Still running on epyc7 (ot-run, alive with CPU at 15:2x UTC; do not relaunch)
- ab/t21_nokeep/gen/slice_station__t21 (S81, R-FLOW without GPL keep): in 6_report/sign-off; hold budget 2.96 % OK.
- ab/coll_ftc_old/gen/coll_ftc (QC old): detail route iter 2 (it0 102,166 viol, it1 12,052).
- ab/coll_ftc/gen/coll_ftc (QC R-FLOW + keep): detail route iter 1 (it0 96,877, same class as old).
- ab/coll_ftc_nokeep/gen/coll_ftc (QC R-FLOW no keep): detail route iter 0 end.
- Launcher logs intel2 ~/rules-flow-1-logs/<arm>.otrun.log; status `bash ab/st.sh 0`.
- Old coll_ftc sign-off for reference: 2,280 slew pins, setup -90.92 / 49, FF hold -16.48 / 347.

### R-FLOW-7 (GPL_KEEP_OVERFLOW 0.25) planned decision
HEAD turn_b keep vs no keep: neutral (slew 0 both; +100.52 vs +99.02; hold -24.27/32 vs -16.72/27). Decide from t21 vs t21_nokeep
and coll_ftc vs coll_ftc_nokeep: keep in the default only if no-keep is not better on setup/hold/cells on S81 and QC; otherwise drop
gpl_keep_overflow from gen_phys.RFLOW + rflow_cfg + tests in a NEW commit and keep it opt-in (HBM resume).

### Max wire 50 um item (COORD 07:2x; HOLDTAP-FIN-2 t41 +78k buffers, +28.9 % area, 353k -> 560k cells)
- Source: not a gen arg (S81 wave passes --max-wire-um 100, QC 120). tools/die_plan/relay_bay.py (SAFE-STATION-1 relay-bay form,
  class default for wire-only station kits S81 slice_station*, QC *_stm_*/*_fw_*/*_fe_*) writes the SMALLEST per-hop BUFx4 pitch
  that gives TT setup and FF hold >= +10 % (83.3 ps) after a 30 ps skew bound into the kit-wide OT_MAXWIRE_UM; R-FLOW's "smaller
  explicit wins" keeps it.
- Probe rows (relay_bay_hop_rows.json) for the t21 hops (231-245 um): pitch 50 -> slew 56-61 ps, setup +561..+574, hold +88..+99;
  pitch 100 -> slew 81-90 ps, setup +594..+608, hold +63..+78 (positive, just under the +83 margin).
  So 50 um is NOT a slew need: it is repeater delay used as hold pad on zero-logic ft hops, then applied to every net of the kit.
- Reading: structural cause = hop hold margin bought by kit-wide buffering. HEAD signed hd_turn_a at 120 (ECO) and turn_b is slew-clean
  at 120. Proposed (NOT built, no A/B yet): relay-bay kits keep the R-FLOW 120 / die 100 kit-wide max wire; the hop hold margin goes
  to R-CLOCK's hold build (or the pitch is applied to the ft lane nets only). Needed A/B: t21 R-FLOW arm with OT_MAXWIRE_UM 100 vs
  ab/t21 (50); compare buffers, area, GRT time, routed hold on the ft hops. No default change until then; list as OPEN measured item.

### ECO slew-margin item (HEAD-97 06:46)
prd_mk.sh variant.env writes OT_SLEW_MARGIN=20 for b/m/t passes. HEAD-97 signed hd_turn_a with OT_SLEW_MARGIN=50 +
OT_PRD_MAX_WIRE_LENGTH=120 (one proof, no A/B). Proposal: R-FLOW-8 ECO defaults 50 / 120; OPEN until an A/B on a second kit
(test_prd_margins.py asserts the 20 baseline and would need an update).

### To finish (RULES-FLOW-1)
1. Collect t21_nokeep + coll_ftc trio; decide R-FLOW-7. 2. Update RULEBOOK R-FLOW (status, proof 2/3/4 rows above, max-wire and ECO
open items, per-kit-class default list) once HOLDTAP-FIN-2's R-CLOCK edit is committed. 3. Push branch, READY to ROOT-MERGE + COORD.

HANDBACK 2026-11-13 07:27 to RULES-FLOW-1
