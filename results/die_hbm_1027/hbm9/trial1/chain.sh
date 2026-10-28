#!/bin/bash
# DIE-HBM-9 first HBM clock-only GRT: C21 plan, inverter tree (QC-11 patch_inv.py pre-READY on a private tool copy), fall/rise + MPW readout
set -e
cd /srv/opentallas-scratch2/claude/die-hbm-9/trial1
ulimit -v 64000000
python3 -I /srv/opentallas-scratch2/claude/die-hbm-9/invroot/tools/die_plan/die_trial.py kit /srv/opentallas-scratch2/claude/die-hbm-9/c21/die_plan.json --out /srv/opentallas-scratch2/claude/die-hbm-9/trial1/kit --region-trees /srv/opentallas-scratch2/claude/die-hbm-9/c21_part_region.json --feed /srv/opentallas-scratch2/claude/die-hbm-9/c21_feed.json --tree-form link_htree --rep-um 250 --tree-site-legal --tree-site-slide --leaf-um 200 --clock-cell inv > kit.log 2>&1; echo "kit rc $? $(date)" >> chain.status
python3 -I /srv/opentallas-scratch2/claude/die-hbm-9/invroot/tools/die_plan/clock_body_bays.py /srv/opentallas-scratch2/claude/die-hbm-9/c21/die_plan.json /srv/opentallas-scratch2/claude/die-hbm-9/trial1/kit/clock/tree.json --out /srv/opentallas-scratch2/claude/die-hbm-9/trial1/bays > bays.log 2>&1; echo "bays rc $? $(date)" >> chain.status
python3 -I overlay.py > overlay.log 2>&1; echo "overlay rc $? $(date)" >> chain.status
ulimit -v unlimited
(bash run_clock.sh TT > grt_TT.log 2>&1; echo "grt TT rc $? $(date)" >> chain.status) & (bash run_clock.sh FF > grt_FF.log 2>&1; echo "grt FF rc $? $(date)" >> chain.status) & wait
python3 -I duty_eval.py c_TT/arr_TT.txt c_FF/arr_FF.txt duty_trial1.json > duty.log 2>&1; echo "duty rc $? $(date)" >> chain.status
