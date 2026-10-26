#!/bin/bash
D=/srv/opentallas-scratch2/claude/master-plan-r6-1026; cd /srv/opentallas-scratch2/claude/wt/master-plan-r6-1026
Q=/srv/opentallas-scratch2/claude
run(){ n=$1; shift; rm -rf $D/$n; prlimit --as=40000000000 /usr/bin/time -v python3 -u -X faulthandler tools/die_plan/die_infra.py master-plan "$@" --out $D/$n > $D/$n.log 2>&1; }
B1E=$Q/path-hbm/b1e_1026/plan_b1e
QC="/srv/opentallas-scratch2/claude/codex-qc-master0733/physical/die_plan/qwen_compute/candidate_oneqc0733.json --mesh $Q/claude-infra-qc-1026/b3 --tracks $Q/infra-first-0140/qc0/pre2/preroute.json --ir $Q/codex-aux-pg-1026/qc/psm_bumponly/core_centre/result.json $Q/codex-aux-pg-1026/qc/psm_bumponly/io_ucie_kv_u_ucie_kv/result.json --entries /srv/opentallas-scratch2/claude/master-plan-1026/entries_qc.json --core-islands /srv/opentallas-scratch2/claude/master-plan-r3-1026/su_islands.json"
run hbm_b1e_reg $B1E/die_plan.json --entries $B1E/entries.json --tree-commensurate regional &
run hbm_b1e2_reg $D/plan_b1e2/die_plan.json --entries $D/plan_b1e2/entries.json --tree-commensurate regional &
#run qc_r6_8x8_reg $QC --tree-commensurate regional &
#run qc_r6_c4x4_reg $QC --tree-lattice c4x4 --tree-commensurate regional &
wait
