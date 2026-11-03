# TOK-QW-5 (Qwen/KV token path; succeeds TOK-QW-4, died ~00:40 11-03)

## 2026-11-03 03:31 PST START
- Worktree rtx-pro /srv/opentallas-scratch/claude/wt/tok-qw-5, branch claude/tok-qw-5-1103 from claude/tok-qw-4-1102@75c22e1fa (READY 00:13, not yet on main).
- Collected [CHECKED]: KV NOWAIT veh60 intel1 oth-ubuntu-2990777: frozen since HB 40000 (frames 7405, boot_go 0 to HB 100000) = defined FAIL (COORD 00:2x); STOPPED (own lane unit). QC census2 (whole tb_qcdie json-only, ROM_TILE defparams removed): MEMCG-OOM again at 64 GiB 00:22 -> defparams are NOT the cause. Per-type census (119 bound types, run_all): all rc 0, RSS 5.6-5.75 GB each, JSON 15 MB (cb) .. 366 MB (sc types). epyc2 tload dirs = done 00:13 work, nothing running.
- COORD: HEAD_TABLE_INSTALL_START = BOOT; KV token runs wait for DIE-KV-63 START join.
