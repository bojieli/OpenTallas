cd /srv/opentallas-scratch2/claude/wt/die-kv-40
python3 tools/clk/ot_clk.py check tools/clk/configs/kv_e26a.yaml > /srv/opentallas-scratch2/claude/die-kv-40-1029/clk_check.log 2>&1; echo CHECK_RC $? 
python3 tools/clk/ot_clk.py replay tools/clk/configs/kv_e26a.yaml --out /srv/opentallas-scratch2/claude/die-kv-40-1029/clk_ctl > /srv/opentallas-scratch2/claude/die-kv-40-1029/clk_ctl.log 2>&1; echo CTL_RC $?
python3 tools/clk/ot_clk.py replay kv40/cfg/kv_e26a_w243.yaml --out /srv/opentallas-scratch2/claude/die-kv-40-1029/clk_w243 > /srv/opentallas-scratch2/claude/die-kv-40-1029/clk_w243.log 2>&1; echo W243_RC $?
