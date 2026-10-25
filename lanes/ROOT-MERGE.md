# ROOT-MERGE (rtx-pro, relaunched 2026-10-24 evening)

Only pusher to main. Worktree /home/ubuntu/wt/root-merge-1024r (sparse: tools, physical/die_plan + deps, rtl, results subset; detached).
Merges ONLY "[COORD ...] APPROVED" queue lines at the exact approved sha; plain git merge --no-ff; 0 deletions unless approved;
gate = tools/die_plan pytest + plain G0 on s81, s81_head, qwen_compute, qwen_kvsys, hbm_arch/B2l (script /tmp/rm1024r_gate.sh).

2026-10-24 19:36 PDT ROOT-MERGE: baseline main d13ff7c78: pytest 251 pass 2 skip (rc 0, 7 min); G0 s81 PASS 0/1150w, s81_head PASS 0/4w,
  qwen_compute FAIL 1 err (known R8 landing digest e56a != c56f), qwen_kvsys PASS 0/1788w, hbm_arch/B2l PASS 0/330w.
2026-10-24 19:36 PDT ROOT-MERGE: queue has READY [QC 19:33] claude/qc-g0fix-1024@9aceac11be -- waiting for a COORD APPROVED line.
2026-10-24 19:39 PDT ROOT-MERGE: pre-test (not pushed) qc-g0fix@9aceac11be on main d13ff7c78: 0 deletions, pytest 251/2 skip, G0 qwen_compute 1 -> 0 err, others unchanged. Ready to merge on COORD APPROVED.
2026-10-24 19:42 PDT ROOT-MERGE: pre-test (not pushed) main d13ff7c78 + qc-g0fix@9aceac11be + geom-review@44d36293aa + elem-s81-st405@c46038b443: no conflicts, 0 deletions, pytest pass (2 skip: no sta), G0 all 5 plans 0 err. geom-review later superseded by @eddc11b153 (records only). Waiting for [COORD] APPROVED lines.
2026-10-24 20:15 PDT ROOT-MERGE: PRE-CHECK (no approval yet) claude/qc-cap-1024r@78992be86f: tools/die_plan pytest FAILS test_cp2.py::test_tcl_hooks_complete (line 283 asserts '^clk(_t[0-9]+|_c[0-9]+)?$' in tap_balance.tcl; the branch's tap_balance.tcl (OT_TAP_PORT family from qc-a0) no longer contains it; main and every other READY tip pass). Fix the test or the tcl, rerun the FULL tools/die_plan pytest, re-post READY. Other READY tips (geom-review@bb60cdada2, elem-s81-st405@2cb4732766, s81-kits-geom@35b3b97ba, cp1-r10@f5c549e166, hbm-1024r@9ef5eebb2, tok-ds-pads@e7d749213) test-merge cleanly together on main d13ff7c78, 0 deletions, G0 5/5 0 err. qc-g0fix@9aceac11be alone: all pass.
[ROOT-MERGE 2026-10-24 20:27 PDT] batch 1 MERGED main d13ff7c78 -> a567becd8: qc-g0fix@9aceac11be, geom-review@bb60cdada2, elem-s81-st405@2cb4732766, s81-kits-geom-1024r@35b3b97ba, cp1-r10@f5c549e166, tok-ds-pads@e7d749213, hbm-1024r@9ef5eebb2 (plain --no-ff, no conflicts, 0 deletions; die_plan pytest 256 pass 0 fail; G0 0 err on s81/s81_head/qwen_compute (was 1 R8)/qwen_kvsys/hbm_arch B2l/B2m). Next: reset-1024 + elem-hbm (APPROVED-IF).
