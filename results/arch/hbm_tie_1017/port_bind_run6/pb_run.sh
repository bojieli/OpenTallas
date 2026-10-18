#!/bin/bash
D=/srv/opentallas-scratch/claude/hbm-tie-1017; cd /srv/opentallas-scratch/claude/hnl-d4f-tp192
A="$(cat $D/pb_cmd.txt) --rtl-file $D/ot_hbm_pc_refresh_cfg.sv --rtl-file $D/cl2.sv --prefer $D/cl2.sv --pad-file $D/die.v.pads.json --top hbm_v16_die --allow-model ot_hbm3e_phy_rc_e8p5"
python3 -I tools/die_port_bind.py $D/die_tie.v $A --out $D/pb_tie_strict.json > $D/pb_tie_strict.log 2>&1; echo strict rc=$?
python3 -I tools/die_port_bind.py $D/die_tie.v $A --strap-file $D/straps_tie.json --out $D/pb_tie_declared.json > $D/pb_tie_declared.log 2>&1; echo declared rc=$?
tail -1 $D/pb_tie_strict.log; tail -1 $D/pb_tie_declared.log; grep FAIL $D/pb_tie_strict.log | head -40
