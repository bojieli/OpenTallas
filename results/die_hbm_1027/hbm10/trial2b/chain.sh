#!/bin/bash
# DIE-HBM-10 trial2: HBM clock-only GRT on C22 with MAIN die_trial (RM150 DIE-QC-11 --clock-cell inv2, even inverters per leg)
# (trial1 = DIE-HBM-9 private pre-READY tool copy, --clock-cell inv on C21: still running, collected separately)
cd /srv/opentallas-scratch2/claude/die-hbm-10/trial2b
ulimit -v 64000000
python3 -I /srv/opentallas-scratch2/claude/wt/die-hbm-10/tools/die_plan/die_trial.py kit /srv/opentallas-scratch2/claude/die-hbm-10/c22v/die_plan.json --out /srv/opentallas-scratch2/claude/die-hbm-10/trial2b/kit --region-trees /srv/opentallas-scratch2/claude/die-hbm-9/c21_part_region.json --feed /srv/opentallas-scratch2/claude/die-hbm-9/c21_feed.json --tree-form link_htree --rep-um 250 --tree-site-legal --tree-site-slide --leaf-um 200 --clock-cell inv2 > kit.log 2>&1; echo "kit rc $? $(date)" >> chain.status
python3 -I /srv/opentallas-scratch2/claude/wt/die-hbm-10/tools/die_plan/clock_body_bays.py /srv/opentallas-scratch2/claude/die-hbm-10/c22v/die_plan.json /srv/opentallas-scratch2/claude/die-hbm-10/trial2b/kit/clock/tree.json --out /srv/opentallas-scratch2/claude/die-hbm-10/trial2b/bays > bays.log 2>&1; echo "bays rc $? $(date)" >> chain.status
python3 -I overlay.py > overlay.log 2>&1; echo "overlay rc $? $(date)" >> chain.status
ulimit -v unlimited
(bash run_clock.sh TT > grt_TT.log 2>&1; echo "grt TT rc $? $(date)" >> chain.status) & (bash run_clock.sh FF > grt_FF.log 2>&1; echo "grt FF rc $? $(date)" >> chain.status) & wait
python3 -I duty_eval.py c_TT/arr_TT.txt c_FF/arr_FF.txt duty_trial2.json > duty.log 2>&1; echo "duty rc $? $(date)" >> chain.status
