#!/bin/bash
# QC-PLAN-F4A master plan on the F4A delta plan (same flags as MASTER-PLAN-R6 qc_r6_c4x4_reg)
D=/srv/opentallas-scratch2/claude/qc-plan-f4a-1026; cd /srv/opentallas-scratch2/claude/wt/qc-plan-f4a-1026
Q=/srv/opentallas-scratch2/claude
rm -rf $D/qcf_f4a_c4x4_reg
prlimit --as=24000000000 /usr/bin/time -v python3 -u -X faulthandler tools/die_plan/die_infra.py master-plan $D/plan/candidate_f4a.json --mesh $Q/claude-infra-qc-1026/b3 --tracks $Q/infra-first-0140/qc0/pre2/preroute.json --ir $Q/codex-aux-pg-1026/qc/psm_bumponly/core_centre/result.json $Q/codex-aux-pg-1026/qc/psm_bumponly/io_ucie_kv_u_ucie_kv/result.json --entries $D/plan/entries_f4a.json --core-islands $D/plan/su_islands_f4a.json --onramp-bays --drop-mesh-early --tree-lattice c4x4 --tree-commensurate regional --out $D/qcf_f4a_c4x4_reg > $D/qcf_f4a_c4x4_reg.log 2>&1
