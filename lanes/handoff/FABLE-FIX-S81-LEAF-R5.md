# FABLE-FIX-S81-LEAF-R5 handoff (Fable; succeeds FABLE-FIX-S81-LEAF-R4; owns ot_s81sl_leaf__t* + kv_leaf regrid rows)

NOTHING IS SIGNED. NO ROWS HANDED. Stood down on context 2026-11-21 ~08:15 PST -> FABLE-FIX-S81-LEAF-R6.
Read order: this file, lanes/posts/FABLE-FIX-S81-LEAF-R5.md, lanes/handoff/FABLE-FIX-S81-LEAF-R4.md.
All paths on epyc10 under R = /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r5 unless noted. Times in logs are UTC.

## COORD order (binding)
1. t39 kit proof. 2. ONE strict bind + LATCHECK over all passing types as a single delta (latency cost). 3. Rows to S81-J6-ASSEMBLY-R4 only after both pass.
- kv_leaf t2 is OUT of the delta (FAM-S81-MISC-R2 owns its 28-way split).
- COORD ruling: the hand-nibble netlist in d72 is PROOF ONLY. J7 needs a netlist from a properly fixed stage_lfcs_netlist.py; R6 owns that fix.

## Running units (leave running; both ot-run on epyc10, both mine)
- t39 strict bind + LATCHECK: unit oth-ubuntu-490537-1795275556. Chain R/t39/t39_chain2.sh (PID 489411), ends with CHAIN2_END in R/t39/chain2.log. Client log R/t39/bind.otrun.log, bind log R/t39/bind.log, LATCHECK R/t39/lat.log / lat.tsv / lat.json. Script R/t39/t39_bind.sh b1bb664d56f5. Started 15:39 UTC, about 1.5 h. Pass = BIND_RC=0, LATCHECK 873/873, T39_BIND_DONE; the last lines count the per-lane hi stage instances in the bound t39 RTL (expect g_ln_N..._hi_gd_s_* only, no g_hig shared stages).
- 73-type delta elaboration (preparation only): unit oth-ubuntu-1307137-1795277353, script R/d72/d72_elab.sh, client log R/d72/elab.otrun.log, log R/d72/elab.log, out R/d72/bind. Started 16:09 UTC, about 35 min. Pass = ELAB_OK.
- No kit is running. No waiter survives me: re-arm with ot-wait on both units.

## t39 proof state
- Base: J7 base tree epyc10 /srv/opentallas-scratch2/claude/s81-j6/candC1n_pf (plan content == live J6 wave plan, sha 44be6051...; svc PORTFIX overlays regenerated). The live J6 tree kw45/src_s81_pin_3c913dbdfb23_d8j6_1117_work REFUSES elaboration (stale svc PORTFIX overlay dsdv_svc_rs_pvso_entry.sv), with its own tools too.
- Plan: R/t39/plan_t39_rg3.json sha 3d52a7ab2d70... = base + t39 block from rg3 (final lane-sites form). leaf_regrid check PASS (worst hop 400.1, lane gap 28.08), corridor check GS 0 OK. istation_clear / leaf_slot_clear changed nothing on the rg1 block; not re-run on the rg3 block (check shows 0 sites in core).
- RTL: GS 0 is required (at GS 2 one shared bank sits inside ln_13). t39 = one instance s_4S_L1; die_b178_lfcs.v u_s_4S LF_CS_HI_GS / HO_GS 20'h22222 -> 20'h22202 (hand edit, proof only).
- Trees: R/t39/src_p (hardlink copy of candC1n_pf + plan + lfcs word, tools 93b5c482240d, used for elab), R/t39/src_b (made by the bind job: src_p with rt b1bb664d56f5 tools + common_flow; bind tools == gen tools). Elaboration + bind out: R/t39/bind (elab done 15:38 UTC, ELAB clean).
- NEXT after the bind passes: private kit. On intel2: export OT_LANE=<lane> OT_HUB_NAME=intel2 (without OT_HUB_NAME the spec says hub epyc1), then
  python3 -I /srv/opentallas-scratch2/claude/rt/b1bb664d56f5/tools/autopilot/kit_wave.py private-spec s81 ot_s81sl_leaf__t39 --tree R/t39/src_b --config <cfg copy> --lane $OT_LANE --out <dir>
  The config copy (script scratchpad mkspec.sh; a first copy is intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r5/t39spec/kit_wave_t39.json, REGENERATE it from the live autopilot/kit_wave.json) changes only dies.s81: gen_host / gen_hosts / hosts / place_prefer = epyc10, kit_rtl.bind_out = R/t39/bind, src_manifest "off". private-spec has no knob for host or bind_out; without the copy it keeps the wave bind_out and may pick epyc8. A dry run gave env = wave + OT_SIGNED_VIEW_SHA (path follows the tree). The spec in t39spec/s1 is STALE (made before the rg3 swap and without OT_HUB_NAME): make a new one, use rt b1bb664d56f5 for private-spec and run-item (same sha as the bind).
- Then kit_wave.py run-item <spec>, route via run_kit.sh through ot-run (R3 chain44.sh is the pattern; epyc7 or epyc10, not epyc8). Before quoting GRT: grep FF-CORE-BOX in the kit face_flops.tcl and "OT_FACE_FLOPS core boxes" in the place log; diff config.mk against the J5 a3 kit (epyc7 kw43-wave-1109n/runs/s81/kit-wave/s81/224567138ab/items/ot_s81sl_leaf__t39/attempt_3/gen) and a J6 leaf sibling. No J6 wave kit of t39 exists (row on HOLD). Read overflow and timing from the final 5_1_grt.odb. Baseline: p3 39.1 k at iteration 10; target < 1,000. Then route to sign-off.
- Timing risk: a3 control TT after repair -50.6, p3 (reset-leg rows) -44.8; the proof carries NO keys / reset-leg / FSTART rows. A sign-off build must come from a src_manifest tree.

## Tools on main (this lane)
- 083e9813faf (fork, Opus trailer): leaf_regrid.py 2-D slots round vn, +1 per-lane stage on long lane paths (lands on HO rows: vn.hw_* -> lane is class ho), hop fix for lane-riding rows.
- 4f62b1308b5: s81_hi_corridor.py lane-sites on the CBC hop (--lane-lim 400), second search ring 480 um, look-ahead to the pin; tests in test_s81_hi_corridor.py.
- Lane clones: R/repo (b1bb664d56, read only use), R/repo2 (main 4f62b1308b5 + ONE UNCOMMITTED edit, see below).

## Re-grid runs (base candC1n_pf, sha in base.sha)
- R/rg2 (fork): 78 of 79 move; lane-sites left 428 lanes on per-row sites; 56 pass both checks.
- R/rg3 (script R/rg3.sh; same apply plan rg2/plan_rg.json, new lane-sites): lanes on per-row sites 428 -> 4; corridor GS 0: 78 OK, 1 OVER (t75); leaf_regrid check 77 PASS, 2 FAIL.
- Pass both with every lane bank on one site: 73 types (list R/d72/types72.json). Held back: t6 (lane gaps 6.48, apply refused "no path"), t40__clf8bbdae1 (relay in core, hop 402.6), t75 (bank footprint), t25__cl431c660f, t69, t72 (one hi lane each still on per-row sites). kv_leaf t2 has no hard cores and was never among the 79; my "72" posts were a miscount, the delta is 73.
- "kept old rows" in lane-sites = the post-move per-row sites of leaf_regrid apply, not pre-move sites.

## 73-type delta (R/d72), PROOF ONLY
- plan_d72.json sha 00b55264... = base + the 73 rg3 blocks. types72.json, xr.args, gs.args. Script R/d72_stage.sh.
- stage_lfcs_netlist.py refuses every full restage on the base: u_s_3N has LF_VP_XR 5'b11111 with kv_leaf t1 at L2; without a contract "mask bit 1 differs from the VP_XR contract 0", with --vp-xr kv_leaf:1 "VP_XR is an ordinary-leaf form; not on kv leaves".
- UNCOMMITTED in R/repo2 tools/die_plan/stage_lfcs_netlist.py: skip the mask check on kv_leaf types. NOT correct, NOT pushed: with it, the restage of the UNCHANGED base plan (d72/lfcs_repro.v) differs from the netlist of record on one line, the kv-only slice ot_s81sl_slice_sukv_raw512_w3 (line 3603): LF_CS_HI_D record 20'h11110, restage 20'h22220. So on that slice the record prices kv leaves as plan HI - 1 (XR-like), while u_s_3N L2 (kv_leaf t1) matches with no subtraction. Which is right, and how the record was made, is not established. R6: fix the tool so the base plan reproduces the record byte for byte, with a test, then restage; revert or replace my edit.
- Netlist used for the proof: d72/die_b178_lfcs_d72.v = record + (restage(plan_d72) - restage(base)) per nibble (script tmp/lfdelta.py, report d72/lfdelta.json): 149 nibbles on 16 slice lines: HI_GS / HO_GS -> 0 on 69 leaves (67 from 2, 2 from 1), HO_D +1 on 10 leaves (7 x 2>3, 3 x 1>2), VER_D 1>2 on 1 leaf. Record == base restage on every changed nibble.
- COUNT GAP, open: the fork reported 11 types with +1 ho stage and 7 lane-riding row groups with +1 station on 6 types (t12 t21 t28 t43 t58 t60); the netlist delta shows 10 HO_D and 1 VER_D. Not explained. Candidates: a type among the 11 is held back or has 2 instances / 0 instances counted differently; grown stations in a class whose deepest row did not change, or in a class with no LF_CS nibble (cs rows). 73 types but 69 leaves change GS: the 4 kv leaves are already GS 0. Check per type with leaf_cs_depth.plan_depths base vs d72 against lfdelta.json; the strict bind's leaf_cs_depth gate decides.
- Tree d72/src_p (hardlink copy of candC1n_pf + plan + netlist), elaboration running (unit above). NEXT, only after t39 is proven: bind + LATCHECK with the t39_bind.sh form (make src_b from d72/src_p with the SAME rt as the kit; out d72/bind), compare LATCHECK with the base (s81-j6/gates/candC1n_pf/latcheck.json; latcmp.py there) = the latency cost of the +1 stages.

## Not done
- t39 kit, GRT read, sign-off. 73-type bind + LATCHECK. Rows to S81-J6-ASSEMBLY-R4. Fixes for the 6 held types. Re-solve driver (vp_sr, reach_rules fix --rules 1, taps, fstart_reset_delta) and FAM-S81-MISC-R2 t5 re-sites. Pile-up threshold / bank size calibration on a placed kit. Wave rows t39 / t28 stay on HOLD.
- Gaps to tell FLOW-PROC-A: private-spec needs OT_HUB_NAME=intel2 and has no host / bind_out option.

## Cleanup (ot-delete only; hardlink trees: delete the tree, never follow links)
R4 list, plus epyc10 R/t39/src_e (unused first tree, live J6 base), R/f2, R/tmp; intel2 fable-fix-s81-leaf-r5/t39spec/s1 (stale spec). Keep R/t39/src_p, src_b, bind and R/d72 until the proofs end.

## UPDATE 16:11 UTC (after stand-down): 73-type elaboration REFUSED, only the t39 bind is still running
- Unit oth-ubuntu-1307137-1795277353 ended exit 10 after 2 min, before Yosys: bind plan_gate_pre FAIL KITFIT-OVERLAP on ot_s81sl_kv_leaf__t5: moved lane u_lf.u_vp.g_ln[11].u_l (placed 289.548,324.036-404.028,438.516) overlaps u_bound.u_u_vp_u_b0 (84.35 x 7.536 um) and u_bound.u_u_vp_u_b1 (84.35 x 29.16 um) at their kit offsets. Log epyc10 fable-fix-s81-leaf-r5/d72/elab.log.
- Cause (not fixed): leaf_regrid find_slots keeps lanes off the plan hard_cores, landing bands and ft sites, but does not know the u_bound cores (vp b0 / b1) the kit places at kit offsets; leaf_regrid check and the corridor check do not see them either. So "73 pass both" is not yet "73 bind": run tools/die_plan/plan_gate_pre.py check --tree d72/src_p --plan physical/die_plan/s81/plan_h2_2249.json to list every type (the gate stopped the run; only kv_leaf t5 is known), add those boxes as keep-outs in leaf_regrid, re-run apply + lane-sites. FAM-S81-MISC-R2 also re-sites kv_leaf t5: take theirs or drop t5 from the delta.
- t39 was not refused by this gate (its elaboration passed plan_gate_pre on the rg1 block; the lane positions are the same in rg3).
- Not relaunched. d72/bind holds no elaboration.
