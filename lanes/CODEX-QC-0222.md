# QC takeover 2026-11-08 02:22

## CODEX notes

2026-11-08 02:24 PST: CODEX took over remaining QC cores, types and numeric/provider integration. No merges, tags or plan-of-record edits. Types owned by Codex QC/types, SU1 production-calendar diagnostic owned by QC/su1.

- QC cores 25/26 (latest forced scan); NL already credited. Only NK open.
- NK vR7 first route healthy on intel1: /srv/opentallas-scratch2/claude/codex-nk-vr7-recovered-1551/qfd_tile_nk_a0c_vR7, unit oth-ubuntu-2392441-1794111263. GRT zero overflow, M7, hold repair chunk 1 progressing 4080 edits/3339 buffers but WNS -40.092 ps / TNS -25175.607 ps unchanged since 22:10. Prior CTS all remaining hold paths input-port launched; GRT worst is u_g.n_b_q[396], same parent class. Do not stop or retry; collect at chunk boundary then DRT/finish/signoff. Diagnose shared flow in-chunk parent-hold stall, no signed-off claim.
- Types: vFR FACE-REACH pilot intel1 qct6s/hc2dc_vFR GRT active, latest WNS -50.17 ps/TNS -179994 ps, no terminal result. vPAC LEC96 epyc6 qct6/hc2dc_vPAC_lec96/result active (Docker qct6-hc2-lec96-2048743). Child checks first placed kits, renders and batch failures.
- Wave approved but not yet applied at takeover: QC v4s staged /srv/opentallas-scratch2/claude/qct7/plan_qc53v4s.json + bind_v4s; one batch coll_ftc/coll_ucie/sle_fe_v3. Conservative sle_ctl cl67434795 and allow-congestion sle_st_a cl18eece69 approved. Shared-wave owner notified; no competing edit here.
- SU1 direct-calendar run6 PASS is conditional VM6/CROM9 only. Production parent transport adds request5 + answer4 = VM15/CROM18; old candidate compensation4 mismatches production9. Own-branch bounded diagnostic proceeding without adoption; lane4 VM writes +14 require explicit coverage.
- NL parent cbx_q10 access/private paired LEF/Lib/PG/actual route/STA remains unqualified. Old direct child counts do not close either parent type. SU0 CORE-KS split and coll_core fold exact source/views remain parent-composition blockers.

Next: collect NK final result, fix future hold-loop class safely, collect types at GRT/LEC, production calendar diagnostic; send branch fixes READY and leave adoption to Claude.

## 2026-11-08 02:29 PST collected and READY

- READY codex/qc-parent-hold-src-0222@7f6b7773d8 on intel2 hub: core_flow.apply(grt_nonport_hold=True) stages the already-landed grt_nonport_hold.tcl after existing HB4/cap wrappers and exports the explicit flag. Default generated files unchanged, post hooks/full-path signoff unchanged. Two generated-kit integration cases PASS (direct Python runner; pytest unavailable under isolated system Python). Existing adapter retains its six actual STA fixture proofs from 1551. No live kit writes, physical duplicate, rollout or gate credit. Use only new own kits after geometry review, not original vR7 in flight.
- Exact a10 sle_su_l1 exit143 diagnosis: WATCHDOG stopped epyc4 oth-ubuntu-2546337-1794124835 because SUPERSEDED by attempt12 on current plan, not OOM or DUT failure. a12 epyc6 PLACE active; no relaunch. Fleet owns watchdog record.
- Old NK15m watchdog restart found: intel2 /srv/opentallas-scratch2/claude/dq80/nk15m, unit oth-ubuntu-3283204-1794132969 (02:16). DRT healthy at20% /5021 intermediate violations, not closure. Superseded older form retained; no extra retry by Codex.
- Parent blockers: cbn_q00 hard_landing.capture requires an actual SIGNED landing proof; provisional sle_cland_w515_n is contract-only and lacks provenance.json. Need real provider, no fabricated provenance. cbx_q10 actual native access LEF/Lib + parent PG/route/STA still required; child NL signoff does not qualify parent.

Source worktrees: completed core_flow option /home/ubuntu/codex-qc-parent-hold-src-0222 (own sparse tree; branch 7f6b7773d8). Initial own worktree checkout /home/ubuntu/codex-qc-parent-hold-0222 was interrupted before any edits to avoid an unnecessary full checkout; Git rolled back its worktree registration and left 3.2GB partial files. No unique work/results there; preserved because this takeover forbids deletions. No source/control change to shared checkouts.
