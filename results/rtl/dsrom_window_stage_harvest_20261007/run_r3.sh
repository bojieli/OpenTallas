cd /srv/opentallas-scratch/claude/takeover-ds/window-stage/src_7aa74e8da
/srv/opentallas-scratch/admit.sh 80 -- python3 tools/dsrom_window_stage_hier_physical.py --out /srv/opentallas-scratch/claude/takeover-ds/window-stage/route_r3 --clock-period-ns 0.770 --margin 1 > ../route_r3.log 2>&1
echo $? > ../route_r3.rc
