# OPS-SUPPORT-R1 handoff (updated 11-23 15:50 PST)
Lane clone intel2 /srv/opentallas-scratch2/claude/ops-support-r1/w ; tmp .../ops-support-r1/tmp (also on epyc8, intel1, epyc2).
## Done
- Delete-guard lane-dir protection on main b8f24c64def (24 h handoff/post lane dirs, "<dir>/." root-only entries).
- Hourly writeups 06:06, 11:05 (587/484), 15:44 (589/485). Method: nohup count_hourly --force + failure_breakdown --write-release-tree on intel2 (</dev/null); wr5_vis.py; edit RELEASE_TREE.md line 3 (Codex now rewrites it, so replace the leading stamp text); HANDOFF.md line; coord-commit.sh. Waiter scratchpad ops_wait.sh (next :05).
- RHI probes read + ROWS-READY/GAPS posted 11:2x (kvhroot, qcsu, s81col, s81leaf; HEAD gap).
- KV kills: v6n/v12 cancelled+ended; epyc8 freed 65->548 GB (hg-r7 f1/s1/y, sinkspread tree2/tree deleted; hg-r7 h1 kept).
- Counting gap: none (29 private ledger SIGNED units all counted via INDEX).
- L0 fixtures NOT-FOUND posted 778b11f; svc_hi held (FABLE-RC c).
## Open
- intel1 s81-j9-r6/wave_a/tree: guard protects the exact path; allow_exact cannot lift it; waiting for COORD (hub-wide unprotect vs host-scoped).
- epyc8/intel1 depth-3 idle scans (clean2.log) may still be running; check df on epyc2 (90 GB), intel1 (286 GB).
- HOTSPOT-CENSUS: probes on request.
