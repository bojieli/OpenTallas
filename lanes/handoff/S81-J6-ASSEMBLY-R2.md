# S81-J6-ASSEMBLY-R2 handoff (started 2026-11-20 23:30 PST; successor of S81-J6-ASSEMBLY)

Inputs read: lanes/handoff/S81-J6-ASSEMBLY.md (00:1x section), lanes/FABLE-PD-S81-2340.md.
Work root: epyc10 /srv/opentallas-scratch2/claude/s81-j6/ (scripts chain.sh, mk_cand.sh, gate.sh, census_c.sh, lanefix.py; rtpin/).
Apply order at or before 11-21 13:00 PST: C3d, else C3c, else C1n (never plain C1d).

## 23:3x state
- C1n gate: unit oth-ubuntu-152516-1795245393 (chain PID 120582), plan 44be6051.
- C3c gate: unit oth-ubuntu-207147-1795245549 (chain PID 177099), plan 7ea453a3. Census HOP 7,294, RESET_LEG 519, REGRESS 0.
- C3d gate: unit oth-ubuntu-446307-1795246109 (chain PID 407736), plan 2ea6cd2f, manifest 143c3fea; 17 deltas 5,242 ops; defines 40, reproofs 5; CFX_OVERLAY_OK. Census = C3c.
- Waiters: ot-wait on all three units (background, this lane).
- C3f = C3d + LEAF-R2 key add-on (9 types) + leaf landing_writer_start reach1 (59 types): plan 12e223f3, manifest 143c3fea (= C3d); gate unit oth-ubuntu-949686-1795247137 (chain_r2.sh PID 891127). candC3e = failed compose (ADOPT_MAIN unset), unused; delete later via ot-delete.
- chain_r2.sh = chain.sh with OT_LANE=S81-J6-ASSEMBLY-R2 and ADOPT_MAIN default a4fc295c2a05.
- Apply order now: C3f, C3d, C3c, C1n (first green). Gates C3c/C3d were never queued: ELAB (docker yosys) runs before gate.sh, so gates/<cand> appears late.
- Lever 1 (COORD 23:45): ROM input-stage rows do not exist (rom_pval is output-side). Will gate a replacement variant only if FAM-S81-COL hands a j6_donor_delta.v1 by 10:00 PST; else J7.

## Apply kit (intel2 /srv/opentallas-scratch2/claude/s81-j6-r2-hub)
- j6_pack.sh CAND: gate-log check -> reach 300 -> latcheck into tree -> seal bind -> compose epyc8 d8j6 (link-dest J5) -> bind replicas -> publish_onbase d8j6 on d8j5 (6 hosts incl epyc7) -> out_install verify -> event commit (mk_event_commit_j6.sh, clone epyc10 s81-j6-r2-clone) -> mk_cand_j6.py (lanes/handoff/S81_D8J6_source_candidate_1121.json + S81-D8J6-G0-BASELINE-1121.json; marker without tools_sha).
- j6_apply.sh PACK_OUT: hold_j6.py rep-first holds (lifts J5-only until-J6 holds, keeps rst_rl_137), publish_apply apply --pilot-item dsdv_slice_lepe_mu_LP__t2.
- After apply: first bound-type gen on scheduler rt -> check config.mk defines (RIP1 on lepe LP t2, CFX + SRAMREG on leaf t39) -> kit_wave_edit /dies/s81/tools_sha = that rt sha, hardlink copy in s81-j6/rtpin/.
- Reps: col_h9_r2__t1__cl774acf45__pv11b6518d, col_h9_r1__t1__cl49d7a23e__pv047ea3b3, ot_s81sl_leaf__t39, serdes__t4, slice_station__t36, dsdv_slice_lepe_mu_LP__t2.

## 00:2x state (11-21)
- C3c gate FAILED at bind: stale dead-input defines. Cause: svc H8 proof reprove_svc_h8_bind_source_1120.json (38 defines) had no matching re-proof (reprove39/40 used the pre-H8 generic instances.json and the SRAM .v instead of the _bb.v header). C3d/C3f gates cancelled by exact unit (same refusal, verified with dead_inputs._reproof_matches).
- Fix: rows/reprove40svc/ (proof.json sha c781731e, run.sh = svc40b.sh: instance lines from the proof's 36 declarations, prefer copy without the SRAM .v): MATCH True, ProvenDead OK.
- C3g = C3f + reprove40svc: gate unit oth-ubuntu-1461686-1795248288 (preferred). C3i = C3d + reprove40svc: unit oth-ubuntu-1497655-1795248407 (fallback). candC3e/candC3h = failed composes (C3h: git index.lock race of two parallel adopt2 runs in the shared clone; compose one at a time), delete later via ot-delete. scratch_svc40 = cp -al of candC3f for the reprove.
- C1n gate still in bind (unit oth-ubuntu-152516-1795245393).
- Apply order: C3g, C3i, C1n.
- Token compile: helper agent working out the bound-mode compile on rt f453583d5830 in epyc10 s81-j6/tokc/.

## 01:4x state
- C1n GREEN (unit oth-ubuntu-152516-1795245393 exit 0): bind 0, LATCHECK 873/873, G0 0 new, PRE PASS. Fallback.
- C3g/C3i try1: dead-input fix held; bind 7 errors = HARD_CORE_PARAM_ALL NO_RECORD on svc H8 cores (prov_1119 views have no config.mk). Fix: 10 registry entries from the svc lane's ksrc tools copy (epyc9 fable-fix-s81-svc-r2/ksrc, sources h259 build config.mk) added to each tree's tools/die_plan/hard_core_built_params.json by rows/reprove40svc/hcp_hook.sh (also listed as HOOK in J6_DELTAS.txt). Try1 logs/gates moved to *_try1.
- Gates rerun (ELAB reused): C3g oth-ubuntu-4066259-1795254291, C3i oth-ubuntu-4066377-1795254291 (one of each; read logs/gate_candC3g.log / _candC3i.log).
- Token compile: helper prepared epyc10 s81-j6/tokc (run_tokc.sh ROOT OUT, bound-data mode on rt f453583d5830; needs structural_tops/ in the bind out; root_c3g). Launch: ot-run --mem 24 --threads 8 --hosts epyc10 -- bash tokc/run_tokc.sh tokc/root_c3g tokc/out_c3g once C3g bind is green.
- Pack decision: C3g green -> j6_pack.sh candC3g; else C3i; else C1n by 07:30 PST.

## 03:5x state (after Codex cover 02:18-03:3x)
- Live event still J5 224567138ab; nothing applied.
- C3g/C3i rerun: bind 0, LATCHECK 0, PRE PASS, but G0 27 new (25 svc census 'as-built bits dropped' vs the static pre-H8 census/s81_lanes.tsv + total line + empty reset-wavefront line). Codex svc_bound_edges (reviews_codex_1121): 19/25 pairs bound bits <= planned, 6 have no direct pin edge. Asked COORD (a) C3g with reviewed G0 acceptance vs (b) C1n (current ruling).
- Codex C1n pack-only chain: intel2 PID 3339199 (j6_pack_codex.sh candC1n -> j6_pack_candC1n.out, publish_d8j6.log); waiter armed. mk_cand_j6.py now sets review_before_route all_items + auto_visual_review_skip ["*"].
- Apply = j6_apply.sh j6_pack_candC1n.out after CHAIN_PACKED and the event review fence (COORD).
- J7 FT watcher resumed as rows/j7_cfg7/ft_after_c1n_rdx_elab_1121_r2.sh (rm -rf replaced by rsync --exclude), PID 2912138 epyc10, waits for gate_candJ7RDX_C1n ELAB (unit oth-ubuntu-2466061-1795260431), log logs/ft_after_c1n_rdx_r2.log.
