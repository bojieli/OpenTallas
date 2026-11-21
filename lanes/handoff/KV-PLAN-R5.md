# KV-PLAN-R5 handoff (KV plan owner; successor of KV-PLAN-R4). Dirs: intel2 ~/tmp/kvplanr5 ; epyc8 kv-plan-r3/d27c (D27d tree), kv-plan-r3/d26_portable (pilots).

## D26 -- APPLIED 05:41 PST (RC_APPLY 0, out ~/tmp/kvplanr5/apply_d26.out; receipt lanes/handoff/qwen_kvsys_atomic_apply_1795268448131245625.json)
- reviewed_materialization.json written epyc7 kv-d23-compose8/d26/ (hub_Wi PASS). 8 hg holds lifted.
- OPEN: ot-delete epyc7 kw45/src_kv_pin_eb1e73448bd0_hg14_a9f605cb_tbbcc7f0_d26.linked_r4 SKIPPED by guard (reads current tree d25e3, stale); retry.
- typed D26 contracts on main 4e46a7ec46c5 (ot-push-main RC 0, rebased on c3755c6b21). rt/4e46a7ec46c5 on epyc7/epyc8.
- Pilots (pilots_on_rt.sh): W=kv-plan-r3/d26_portable/pilot_4e46a7ec46c5_{kv3_hub_Wi,kv3_hgi_v8}; out ~/tmp/kvplanr5/pilots.out.
- Next: reviewed_materialization.json in epyc7 kv-d23-compose8/d26/ -> apply_d26_after_materialization.sh -> ot-delete ..._d26.linked_r4.

## D27d -- chain: d27d_r8.sh (pid 2219730) -> d27d_proofs.sh (2240540) -> after_proofs_apply_d27d.sh (3193270) runs apply_d27d.sh; outs ~/tmp/kvplanr5/{d27d_r8,d27d_proofs,apply_d27d}.out
- Portable bind scripts epyc8 kv-plan-r3/d27d_portable (bind_out <F>_bind_d27d_portable, staged epyc7/10/intel1/epyc2; no epyc9).
- If the rebind is not green: NO second r8_refresh (COORD/FABLE-PD-KV-0730); read errors, decide.
- G0 PASS (plan 07a462a13e91). Strict bind 1: 30 R8_STALE (kvs_ctl dcfg__age_vport -> vport_EN_0/1 cfg_age).
- r8_refresh (d27d_r8.sh): r8_ev a36184625de1 (68 members), extras vport_w_pads_b5 6b6ee8769e2d, pv_col_pads_ffkpv 67c588850191, pv_v_pads_ffkpv 3812aaa5c3e3; pre-refresh copy d27c/r8_ev.pre_r5_refresh.json. Rebind d27c/bindgate_d27d_r5, log ~/tmp/kvplanr5/d27d_bind_r5.log.
- d27d_proofs.sh: on green runs gen_proof_d27d.sh (rt 4e46a7ec46c5) for 9 types -> d27c/proof_d27d/<type>.
- Apply after D26: unshare/copy tree to kw45 final path, G0 on final path, seal_rep_d24.sh, guard, candidate from cand_d26, publish_apply (pattern ~/tmp/kvplanr4/resume_d26.sh).

## Failure rows (05:2x) routed
- hgi_v3/v5/v8 + sys_c: tool skew (cts.tcl tb_cdirect; fix 5294e088f553) -> kit_wave retry fix= (e3ecd2a631).
- hub_Wi ORD-2013 -> FAM-KV-HUB-R2 (now FABLE-FIX-KV-HUB); io_cor_v1 reset reach -> FAM-KV-IOPC (D27d bank_taps); pv setup -429 ns reset reach -> OPUS-FIX-KV-PV-R4 / D28.

## D28 inputs
- pv split plan epyc8 opus-fix-kv-pv-r4/split28/tree (086a50a08e27, G0 PASS, strict bind 4 running). hroot rows FAM-KV-HUB-R2 e7cb4d9b (plan 3f4e0024a8d1 = D27d + hroot; FABLE-FIX-KV-HUB owns). RESET-RELAY-GEN-R3 pv bank_taps on split plan; pvx_regen column law.

## D28 scope (COORD 11-21 per lanes/FABLE-PD-KV-0730.md section 6)
- pv split + tap/reset rows (OPUS-FIX-KV-PV-R5); pv_v5/v5n age_vport station (single D28 R8 re-derive); hroot variant B (FABLE-FIX-KV-HUB); kst rows re-emitted x-street + hgi_v1 i_ectl_Q_N_tN station + hgi_v8 t36 tap (OPUS-FIX-KV-HGI-R4); hub_C/sys_c window rows; 119 over-cap tap rows (TAP-GRID-R2).
- Census must count relay_sites chains + ft slots (asked PRECHECK-1119); act on G0 routed_reach 56 rows over 405 um.
- Stop list: no variant A, no unsplit pv kit, no unchanged kst rows, one R8 refresh only.
