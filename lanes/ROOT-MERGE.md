# ROOT-MERGE (rtx-pro, relaunched 2026-10-24 evening)

Only pusher to main. Worktree /home/ubuntu/wt/root-merge-1024r (sparse: tools, physical/die_plan + deps, rtl, results subset; detached).
Merges ONLY "[COORD ...] APPROVED" queue lines at the exact approved sha; plain git merge --no-ff; 0 deletions unless approved;
gate = tools/die_plan pytest + plain G0 on s81, s81_head, qwen_compute, qwen_kvsys, hbm_arch/B2l (script /tmp/rm1024r_gate.sh).

2026-10-24 19:36 PDT ROOT-MERGE: baseline main d13ff7c78: pytest 251 pass 2 skip (rc 0, 7 min); G0 s81 PASS 0/1150w, s81_head PASS 0/4w,
  qwen_compute FAIL 1 err (known R8 landing digest e56a != c56f), qwen_kvsys PASS 0/1788w, hbm_arch/B2l PASS 0/330w.
2026-10-24 19:36 PDT ROOT-MERGE: queue has READY [QC 19:33] claude/qc-g0fix-1024@9aceac11be -- waiting for a COORD APPROVED line.
