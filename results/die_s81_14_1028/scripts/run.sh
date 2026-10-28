set -x
for V in main cal; do
 T=/srv/opentallas-scratch2/claude/die-s81-14/${V}_tools/tools/die_plan; CC=""; [ $V = cal ] && CC="--clock-cell inv2"
 python3 $T/die_sta_related.py /srv/opentallas-scratch2/claude/die-s81-13/proof --plan /srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json --out /srv/opentallas-scratch2/claude/die-s81-14/t1/sta_intra_$V --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions /srv/opentallas-scratch2/claude/die-s81-13/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice $CC > /srv/opentallas-scratch2/claude/die-s81-14/t1/sta_intra_$V.log 2>&1; echo "$V rc $?" >> /srv/opentallas-scratch2/claude/die-s81-14/t1/status
done
