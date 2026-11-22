# FABLE-FIX-S81-LEAF-R6 handoff (Fable; succeeds R5; owns ot_s81sl_leaf__t* + kv_leaf t1 t3 t4 t5)

NOTHING IS SIGNED. NO ROWS APPLIED. Stood down on context 2026-11-21 ~18:3x PST -> FABLE-FIX-S81-LEAF-R7.

## STATE AT STAND-DOWN (18:3x PST; read this first, the sections below are history)
- J7 is SEALED without the leaf re-grid (preferred a6771d121e95, intel2 kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work; apply 11-22 04:15). The leaf re-grid is a J8 item.
- My 69-type gate d8 FAILED 14:03: bind 3 errors = LATCHECK 2 lanes off the table (up_s_2N_L1 and up_s_6N_L2 deliver +2: the grown leafup_o0 groups of t28 / t60, class UNPRICED_KIT_STATIONS). Log R6/d8.otrun.log.
- Codex (limit cover 14:23-18:1x) dropped t28 + t60: rg9 / d9 = 67 types on J7 v5 ec6693a0: strict bind BIND_RC=0, LATCHECK 873/873 PASS, 2 lanes +1 vs base (dn_s_1S_L2, dn_s_6S_L1). Files R6/rg9 (plan_d.json, die_b178_lfcs_d.v, types.json, held.json), R6/d9, log R6/d9.otrun.log, scripts R6/r6_rg9.sh r6_d9.sh. THIS is the first green gate of the re-grid.
- Codex then rebased it on the sealed J7 as 66 types (kv_leaf t5 left to FAM-S81-MISC, "MISC5d"): intel2 /srv/opentallas-scratch2/claude/s81-j6-r2-hub/leaf_followups_codex (rg9_rebased_on_j7, rg9_on_j7_geometry_delta.json, source patch 5cdca2ec226f = 126 LF_CS nibbles, script gate_rg9_rebased.sh). Fresh gate RUNNING: unit oth-ubuntu-1263880-1795310452 on intel2 (Codex's unit, not mine), out gate_2e60f7, client log gate_2e60f7.otrun.log; elaboration done (RG9_ELAB_RC=0) at 18:2x, bind next. NEXT: wait on it (ot-wait oth-ubuntu-1263880-1795310452); green = hand the 66-type rows + source patch to S81-J6-ASSEMBLY-R4 for J8. CHECK that the source patch was made by stage_lfcs_netlist.py (main 44ed532f4d, --vp-xr / --vp-sr / --hi-gs / --ho-gs), not by hand: COORD ruling 2 forbids hand-edited nibbles; stage_rg9_selected.py is Codex's own stager and has not been reviewed by me.
- Codex t28 / t60 follow-up (not reviewed by me): leaf_followups_codex/d8_exact_bank_r5, a six-op donor that prices +2 on up_s_2N_L1 / up_s_6N_L2.
- t39 PROOF KIT DID NOT PASS: route stage exit 6 at 16:33. GRT ended with congestion, total overflow 4,612 (p3 baseline 39.1 k at iteration 10; target < 1,000) and the post-CTS TT gate reads setup_est -178.56 (PLAN-TRIAGE FAIL, < -150). So the re-grid cuts overflow about 8x on t39 but the form is NOT proven to sign-off. Kit K (path below), 5_1_grt.odb exists: read real overflow location and TT from it before any next build (which lanes / gcells; the proof is on the J6 base without keys / reset-leg / FSTART rows, a3 control was TT -50.6). Do not relaunch the same kit.
- Held, second set: t6, t40__clf8bbdae1 (geometry); t21, t25__cl431c660f, t37 (explicit tap tables); t41, t51, t56, t7 (local reset depth); t43 (ver growth plan 2 / bound 1); t28, t60 (leafup depth, Codex donor); kv_leaf t5 (MISC).
- No job of mine is running. Tools on main from this lane: 58ecd8429c, 197076cf03, 2b4fe8f295, 44ed532f4d, 00ff12f70a.

## Done (main)
- 58ecd8429c stage_lfcs_netlist.py: kv leaves with hard cores are XR leaves (HI_D = plan HI - 1, GS 0); the bank leaf kv_leaf t2 is not staged and its mask bit is not priced. Restage of the unchanged J6 base 44be6051 with --vp-xr TYPE:1 on all 79 staged leaf types (R6/tmp/xr.args) is byte-identical to the record (sha 3340107e82f0). R5's skip patch (R5/repo2, uncommitted) is dead.
- 197076cf03 s81_hi_corridor.boxes + leaf_regrid check: content macros (kv leaf u_bound memories) are core boxes; lanes_on_core gate.
- Count gap closed: +1 ho stage on 10 types (not 11), all in the delta; 7 grown groups = 5 bus rows without an LF_CS class + 2 ver groups on t43 in one VER_D nibble.

## t39 proof
- Strict bind 0 errors + LATCHECK 873/873 PASS (R5/t39/bind, plan 3d52a7ab2d70, rt b1bb664d56f5).
- Kit: spec intel2 R6/t39spec/s1/spec.json, chain intel2 R6/t39spec/r6_chain39.sh (log chain39.log, ends CHAIN39_END), run-item log s1/run_item.log, result s1/result.json. Work dir epyc10 kw43-wave-1109n/runs/s81/kit-wave/s81/dc92652f0d5/private/FABLE-FIX-S81-LEAF-R6/ot_s81sl_leaf__t39_1121083024.
- After place: check FF-CORE-BOX in the kit face_flops.tcl and "OT_FACE_FLOPS core boxes" in the place log, diff config.mk vs the J5 a3 kit, then run_kit.sh route through ot-run on epyc10 (R3 chain44.sh pattern), read 5_1_grt.odb. Target < 1,000 overflow at iteration 10 (p3 baseline 39.1 k). A sign-off build must come from a src_manifest tree.

## Re-grid on J7 (COORD / FABLE-PD section 1 / FABLE-CLOSURE-0910 lever 4)
- More tools on main: 2b4fe8f295 (leaf_regrid seats START stages / local resets inside a core; check reads xy_um), 44ed532f4d (stage_lfcs_netlist --vp-sr: plan ho includes the SR output station). J7 identity: restage of J7 v5 with --vp-xr + --vp-sr on 79 leaf types == record.
- The J6-based d72 delta and rg4 (J7 v3) are dead. LIVE: R6/rg5 (script R6/r6_rg5.sh) on candJ7c = J7 v5 plan ec6693a02501: 77 types pass (rg5/types.json), held t6 + t40__clf8bbdae1 (rg5/held.json). Overlay 0 (rg5/ovl.json, script R6/tmp/r6_ovl.py). plan_d.json sha 07eba18750ac, netlist die_b178_lfcs_d.v sha 75a0efe3b598 (args rg5/xr.args sr.args gs.args).
- Rows file: rg5/j7_delta_leaf_regrid_supersede.json (script R6/tmp/r6_mkdelta.py; whole-key replace per type vs the v5 plan). NOT handed until the gate is green.
- Gate: R6/r6_d5.sh via ot-run (--mem 64 --threads 8 --priority plan --plan-job bind), tree R6/d5/src (rsync --link-dest of candJ7c + plan + netlist), out R6/d5/bind, logs R6/d5/elab.log bind.log lat.log latcmp.out, client log R6/d5.otrun.log; ends D5_DONE. Pass = ELAB_OK, BIND_RC=0, LATCHECK 873/873 (expect +1 cycle on the grown groups of t12 t21 t28 t43 t58 t60 only).
- If the J7 base moved past v5 (v6 exists): compare the leaf types of the new plan with v5 (R6/tmp/r6_cmp.py pattern); equal = the delta applies as is, else re-run r6_rg5.sh with K= the new tree and the gate.
- Not re-solved by a tool: landing_contract.collector_tree relay records (6,058) and 9 reset_tree_anchor records under moved cores; the bind judges them. If the bind refuses on resets: reset_anchor.record / fstart_reset_delta.py on the bound tree, then bind again.
- Held types t6, t40__clf8bbdae1 need their own fix (t6: no 2-D path; t40: relay u_u_lf3_u_ve_u_crr_s/q in u_ve.u_s, hop 402.6).

## Gate history (11-21, all epyc10 R6; each = one ot-run job, plan priority)
- d5 (77 types): bind refused t21 explicit tap under a lane -> t21, t25__cl431c660f, t37 held (frozen explicit tap tables; check gate on main 00ff12f70a).
- d6 / rg6 (74): bind refused lane dn_s_1S_L2 fixed_cycles -> assembly lanefix.py (2 lanes: dn_s_1S_L2 2->3, dn_s_6S_L1 8->9; the grown leafdn_i0 groups of t12 / t58).
- d6 / rg7 (74 + lanefix): bind ran to the end, 12 errors on 5 types: t41 t51 t56 t7 landing_local_resets depth != copy depth (the reset tree is re-made under the moved lanes; RESET_ANCHOR finds no same-depth relay) and t43 LF_CS_DEPTH ver plan 2 / bound 1 (grown ver groups). Log R6/d6/bind.log lines 7282-7300. The other 69 types bound clean.
- LIVE: rg8 (69 types = 74 minus those 5; script R6/r6_rg8.sh; client log R6/d8.otrun.log; plan R6/rg8/plan_d.json sha 6e2a8d8d8465; netlist R6/rg8/die_b178_lfcs_d.v; tree R6/d6/src reused with the rg8 plan + netlist; out R6/d8/bind; logs R6/d8/elab.log bind.log lat.log latcmp.out; ends D8_DONE). Pass = ELAB_OK, BIND_RC=0, LATCHECK 873/873.
- When green: build the rows file with R6/tmp/r6_mkdelta.py pointed at rg8 (sed /rg5/ -> /rg8/; ADD the 4 lanefix ops of rg8/lanefix_delta.json, the script asserts top-level equality so relax that for lanes / latency), check the J7 base still equals ec6693a0 on the leaf types (v6 exists), post rows + netlist + gate logs to S81-J6-ASSEMBLY-R4.
- Second set (J8): t6, t40__clf8bbdae1 (geometry); t21, t25__cl431c660f, t37 (explicit tap re-solve); t41, t51, t56, t7 (local resets: fstart_reset_delta.py on a bound tree of the re-grid plan, then bind again); t43 (ver growth: why the bound RTL stays at 1).

## t39 kit
- K = epyc10 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/dc92652f0d5/private/FABLE-FIX-S81-LEAF-R6/ot_s81sl_leaf__t39_1121083024/gen/ot_s81sl_leaf__t39 (run_kit.sh is one level up). Place done, geom PASS, FF-CORE-BOX active. Route stage (CTS + GRT) running: unit oth-ubuntu-243015-1795284663, client log K/otrun_route.log. Wait: ot-wait --kit K --stage grt. Read GRT from 5_1_grt.odb. Then finish / sign-off gates; a sign-off build must be rebuilt from a src_manifest tree (this proof is on the J6 base).
