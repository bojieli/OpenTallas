# FABLE-FIX-S81-LEAF-R6 handoff (Fable; succeeds FABLE-FIX-S81-LEAF-R5; owns ot_s81sl_leaf__t* + kv_leaf regrid rows)

NOTHING IS SIGNED. NO ROWS HANDED. Read order: this file, lanes/posts/FABLE-FIX-S81-LEAF-R6.md, lanes/handoff/FABLE-FIX-S81-LEAF-R5.md, lanes/FABLE-PD-S81-0830.md section 1.
Paths on epyc10 under R6 = /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r6 (R5 = .../fable-fix-s81-leaf-r5). Lane clone R6/repo.

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
