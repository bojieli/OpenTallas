#!/bin/bash
D=/srv/opentallas-scratch2/claude/master-plan-r5-1026; cd /srv/opentallas-scratch2/claude/wt/master-plan-r5-1026
Q=/srv/opentallas-scratch2/claude
run(){ n=$1; shift; rm -rf $D/$n; prlimit --as=24000000000 /usr/bin/time -v python3 -u -X faulthandler tools/die_plan/die_infra.py master-plan "$@" --out $D/$n > $D/$n.log 2>&1; }
run qc_r5_default /srv/opentallas-scratch2/claude/codex-qc-master0733/physical/die_plan/qwen_compute/candidate_oneqc0733.json --mesh $Q/claude-infra-qc-1026/b3 --tracks $Q/infra-first-0140/qc0/pre2/preroute.json --ir $Q/codex-aux-pg-1026/qc/psm_bumponly/core_centre/result.json $Q/codex-aux-pg-1026/qc/psm_bumponly/io_ucie_kv_u_ucie_kv/result.json --entries /srv/opentallas-scratch2/claude/master-plan-1026/entries_qc.json  --core-islands /srv/opentallas-scratch2/claude/master-plan-r3-1026/su_islands.json
