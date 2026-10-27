#!/bin/bash
# QC-MP-REGION-2 master-plan gates (R4 gates.sh inputs + --region-dist)
D=/srv/opentallas-scratch2/claude/qc-mp-region2-1026; cd /srv/opentallas-scratch2/claude/wt/qc-mp-region2-1026
export PYTHONPATH=$PWD/tools/die_plan:/srv/opentallas-scratch2/claude/die-proto-2325/pylib
Q=/srv/opentallas-scratch2/claude
n=${1:-gates_r2}; rm -rf $D/$n
echo "SRC $(git rev-parse HEAD) dirty $(git status --porcelain tools/die_plan | wc -l)" > $D/$n.log
prlimit --as=24000000000 python3 -u tools/die_plan/die_infra.py master-plan $Q/codex-qc-master0733/physical/die_plan/qwen_compute/candidate_oneqc0733.json --mesh $Q/clock128-r4-1026/tree --tracks $Q/infra-first-0140/qc0/pre2/preroute.json --ir $Q/codex-aux-pg-1026/qc/psm_bumponly/core_centre/result.json $Q/codex-aux-pg-1026/qc/psm_bumponly/io_ucie_kv_u_ucie_kv/result.json --entries $Q/master-plan-1026/entries_qc.json --core-islands $Q/master-plan-r3-1026/su_islands.json --tree-lattice c4x4 --region-dist --out $D/$n >> $D/$n.log 2>&1
echo rc=$? >> $D/$n.log
