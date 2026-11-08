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
