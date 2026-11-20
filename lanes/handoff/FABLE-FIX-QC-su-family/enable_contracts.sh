#!/bin/bash
# SONNET-FIX-QC 11-20: re-enable the signed lane clock contracts (mv back) AT THE SAME MOMENT the N46T plan with rows_family.json applies, not before.
# usage: enable_contracts.sh enable|disable
V=/srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_n46_s0/physical/die_plan/qwen_compute/qcviews_1111/views
for h in intel1 epyc2 epyc7 epyc8 epyc9 epyc10; do
 timeout 120 ssh -n -o ControlPath=none $h "for l in 0 1 2 3 4 5 6 7; do d=$V/qfd_qc_su_lane_w_l\$l; chmod u+w \$d; if [ $1 = enable ]; then mv -f \$d/clock_contract.json.SONNET-DISABLED-1120 \$d/clock_contract.json; else mv -f \$d/clock_contract.json \$d/clock_contract.json.SONNET-DISABLED-1120; fi; chmod a-w \$d; done; echo $h $1 done"
done
