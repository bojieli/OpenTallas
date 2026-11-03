# TOK-QW-5 (Qwen/KV token path; succeeds TOK-QW-4, died ~00:40 11-03)

## 2026-11-03 03:31 PST START
- Worktree rtx-pro /srv/opentallas-scratch/claude/wt/tok-qw-5, branch claude/tok-qw-5-1103 from claude/tok-qw-4-1102@75c22e1fa (READY 00:13, not yet on main).
- Collected [CHECKED]: KV NOWAIT veh60 intel1 oth-ubuntu-2990777: frozen since HB 40000 (frames 7405, boot_go 0 to HB 100000) = defined FAIL (COORD 00:2x); STOPPED (own lane unit). QC census2 (whole tb_qcdie json-only, ROM_TILE defparams removed): MEMCG-OOM again at 64 GiB 00:22 -> defparams are NOT the cause. Per-type census (119 bound types, run_all): all rc 0, RSS 5.6-5.75 GB each, JSON 15 MB (cb) .. 366 MB (sc types). epyc2 tload dirs = done 00:13 work, nothing running.
- COORD: HEAD_TABLE_INSTALL_START = BOOT; KV token runs wait for DIE-KV-63 START join.

## 2026-11-03 04:36 PST QC whole-vehicle class found [CHECKED own runs]
- Frontend bisection (verilator --json-only, reduced copies of qwen_compute_bound_top, intel2 memory-capped scopes): none 5.56 GB; slices-only (185 insts) 14.7 GB; cb12 9.25 GB; cb48 21.9 GB; cb48 with ALL strap params stripped 21.8 GB (params are not the cause); cbs-only (192) OOM at 64G; FULL 81.7 GB / 13m55s rc 0 (so census2 at 64G was simply too small; defparams not needed for the blow-up).
- Flattened-node census: one compute block = 19.5M flattened nodes, 88% in 4 x ot_qwen_w12_matvec_part (4.27M each, no ROM, no xref). Whole die ~3.97G flattened nodes: 192 blocks 3.74G + slices 0.23G. build0 (flat, plus 768 ROM_TILE tile specialisations) OOM 360 GiB.
- Class fix (sim/tb-only, no RTL change): (1) Verilator hier_block ot_qwen_w12_matvec_part via hier.vlt; (2) tb ROM loads by hierarchical $readmemh (tools/qwen_tokfunc/current_path/qc_rom_load.py -> rom_load.vh, 7732 loads: 7680 tile + opseg + 51 programme) under +OT_TB_ROM_DIR, ROM_TILE stays -1 (Verilator rejects defparam through g_rb[] arrays, so leaf-level defparams are impossible).
- A/B unit test (one compute block, tiles 708..711: defparam+OT_ROM_DIR vs readmemh) running intel2; build1 whole-QC hierarchical build ADMITTED epyc2 oth-ubuntu-3153048-1793709264 (--mem 160, die, /home/ubuntu/scratch-root/claude/tok-qw-5/build1, chained 6000-cycle bring-up run).
