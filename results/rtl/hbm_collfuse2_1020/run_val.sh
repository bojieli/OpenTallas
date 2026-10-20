#!/usr/bin/env bash
R=/srv/opentallas-scratch/claude/hbm-collfuse2
cd $R/src || exit 9
M=$R/src/results/token_pass/measured_hbm_1019/combined_1020/measured_rel_i8_su.json
PYTHONPATH=tools python3 -m hgi_sim.toksim_bind_validate_1020 $R/val/timing_ref_713c.py --out $R/val/model_all.json --bw 98 --bridge 1 > $R/val/model_all.log 2>&1; echo "model rc=$?" > $R/val/rc.txt
CENSUS_ONLY=info_banklat_all PYTHONPATH=tools python3 -m hgi_sim.toksim_bind_validate_1020 $R/val/timing_ref_713c.py --out $R/val/meas_rel.json --measured $M --bw 98 --bridge 1 > $R/val/meas_rel.log 2>&1; echo "meas rc=$?" >> $R/val/rc.txt
