# QC types takeover 2026-11-08 02:24 PST

CODEX took over: collect QC-TYPES-7/8/7s and FACE-REACH/tap-pair jobs. Shared wave config remains owned by root wave lane; no source branch yet, no launches or POR changes.

## CODEX notes
- RUNNING: intel1 /srv/opentallas-scratch2/claude/qct6s/hc2dc_vFR/gen/slw_hc2__cla3497502__cldc737267, GRT repair_timing. Latest TT WNS -50.17 ps, TNS -179994 ps at iteration 340; earlier -53.3. No terminal verdict, no duplicate.
- RUNNING: epyc6 /srv/opentallas-scratch2/claude/qct6/hc2dc_vPAC_lec96/result, Docker qct6-hc2-lec96-2048743. hyp3.aig written 10:22 UTC; no terminal verdict.
- APPROVED/NOT APPLIED: v4s staged plan + bind_v4s and item_env conservative sle_ctl cl67434795 / allow_congestion sle_st_a cl18eece69, per COORD 02:17. kit_wave.json still v4t / bind_v4t at collection. Sent parent exact action; root wave owns it.
- VIEWED vFR PLACE floorplan/density (copied /tmp/codex-qct-0222/vFR_*.png from intel1 render_place). Fill 5.9%, 613x1339 um; logic packed in bottom third, huge empty upper region; no macros. SMELLS 7 far face reach, 4 sparse clock span, 8 bottom clusters next to empty area. CLASS SPARSE. Running existing repair is preserved; no family batch release from this partial result.
- slw_stm_v2 cl9beb65e6 remains held (old -519.55 ps large setup miss). Sibling cl1ca9c415 still kit_rtl at 01:28; collect it before redesign choice.

Next: diagnose currently unclassified unit/infra failures once; inspect conservative sle_fw_v3 config and tap-pair CTS logs when available; collect vFR/vPAC terminals; class fixes on own branch after actual geometry.

## Canonical runtime collection (intel2; local autopilot snapshots lag)
- sle_su_l1 clc6d66f5b a10 route: intel2 jobs/48b7db32e729/a2.log -> epyc4 unit oth-ubuntu-2546337-1794124835 exited143 after GRT extra iteration24/30; no tool error/OOM evidence. Sender unresolved, journal absent. a12 already active epyc6 unit2939277-1794133187; no relaunch.
- sle_fw_v3 a29 epyc6 unit2937068-1794133181: actual config OT_CLAND_STRIP_ROWS3, OT_CONS_UTIL0.35, MAX_ROUTING_LAYER M7. PLACE active. This verifies conservative ring form but does not assert M6.
- slw_stm_v1 cl05fc43f7 cl389df4e9 a15: wrapper says OSError but actual producer PLACE rc0, 3_5_place_dp written, LEC exit0 at00:53. Parent/wave notified for reconciliation, no rebuild.
- sle_st_a_v2 a16: no-memory admission failure, no P&R verdict. Historical plan; no unchanged retry.
- slw_stm_v2 cl1ca9c415 a7: kit_rtl disk wait intel1 scratch3 since01:29, old bind_strict. Parent/wave notified; no producer claimed and no migration performed here.
- vFR repair continues (-49.62ps at370 edits). Staged cw_n2 source centroid(93.12,131.69) -> north pin(94.14,1339.2), +2 pin cycles; running result needed before any family expansion.

## 02:35 results / active next work
- READY source codex/qct-reset-digest-0222@1aa8d5d7e5 on hub; base289149dea5. Exact tap_pair_affinity exclusion from native reset identity; 10 tests PASS incl actual-reset/unknown-clock mutants. Tree /home/ubuntu/codex-qct-digest-src-0222. No source adoption/merge/tag/POR. Initial worktree checkout was interrupted at8% to avoid a full checkout; partial own /home/ubuntu/codex-qct-digest-0222 preserved; subsequent source worktree is sparse.
- a10 correction: WATCHDOG explicitly SUPERSEDED by current-plan a12. Legitimate auto-stop; not hung/OOM. Sender now known, no failure left undiagnosed.
- Found all4 missing CBN ring variants already SIGNED on epyc5 qc-cbn-rf1/kits/*_hcbn1106, TT+151.56..157.81,FF+16.04..22.84,DRV/DRC0. Wrapper failed only pin_audit /work parents[5] IndexError after signoff. Existing LEC synthesis EQUIVALENT, not routed.
- Exported actual5 providers to epyc5 /srv/opentallas-scratch2/claude/codex-qct-providers-0222/views_old/{sle_cland_w515_n,sle_cland_w515_n_300,sle_cland_w515_n_301,sle_cland_w517_s_300,sle_cland_w517_s_301}. Export complete:true all4 variants; base copied existing actual signed export. Current-main hard_landing capture+prove PASS all5; portable landing_evidence present. Requested master/depth4/WREG1/WFALL1 identities match;1042/1046 plan pin names/layers/faces all match, normal grid snap max0.006um retained. No fake records/current-tag/routedEQ/count claim.
- Viewed cbn_ring_geometry.png (source qc-cbn-rf1 plan image): real N rings at N pins and S rings beside S pins, narrow edge strips; parent huge4macro stack and long reset/FT remain existing obligations. No PLACE/route released from this review.
- Approved by parent: ONE private CBN GEN-only overlay with5realrings and honest NK contract. Queued own intel2 client3745213,16GB2T epyc5 scratch2/codex-qct-providers-0222, script cbn_gen1.py; log intel2 ~/codex-qct-0222-dispatch/cbn_gen1.log. E5 admission -21GB, not yet admitted. No shared wave config/POR edit.
- New STM1cl2086fa2c failure is async-reset recovery: u_core.u_rl.rst -> u_core.u_stream.tag[27], >40 repeaters,617129cells,TT-720.98/2982. Parent informed local-reset subgroup RTL redesign needed; no ECO/retry.
