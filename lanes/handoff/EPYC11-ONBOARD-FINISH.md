# EPYC11-ONBOARD-FINISH handoff (11-24 00:25 PST)
- gen_hosts with epyc11: s81_head only. QC removed e964dadbe57, S81 removed a23c8c744fd, KV never added. No flowops-e11*/e11* unit live; no auto-add can fire.
- QC re-add: postbind_1123203737 140/555 on epyc11; recopy via copy class (FLOW-OPS-R3), verify 555/555 hash 06479c, then kit_wave_edit.
- S81 re-add: hash 3 d8j8 dirs on epyc11 when disk is calm, one job, ionice: tmp/hdirs.py + tmp/hroots_s81.txt; expect bind 54daa9 (3052), postbind scratch2 20fa22 (3052), scratch3 5be9d8 (266). tmp/h2.sh is the launcher (intel2).
- KV re-add: d29 bind 25c829 + postbind 05a992 equal epyc10; src selected_candidate only as .part (partial tar), finish with ot-tree-fork only.
- STUBS: 5 binds, see posts 00:15/00:22; FLOW-OPS-R3 has the names. bound_trees not edited (per die, no host field).
- Monitor: fleet-viz + Explorer show EPYC11; explorer-store-r1/srv pinned at 8f590b7d24e, drop-ins removed (backup in tmp/dropins-bak on epyc8).
- r17b_s0 (48 GB) on epyc11: ot-delete SKIPs (guard); left.
