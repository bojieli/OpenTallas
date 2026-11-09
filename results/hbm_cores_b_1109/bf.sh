cd /srv/opentallas-scratch2/claude/kw35/us
cat summary.txt | cut -c1-200 | head -30
wc -l affected.tsv; head -3 affected.tsv | cut -c1-240
sed -n 1,50p apply.py | cut -c1-170
echo ---- f
df -BG --output=avail,target /srv/opentallas-scratch2 /srv/opentallas-scratch3 / 2>/dev/null
du -s -BG /srv/opentallas-scratch3/claude/kw26-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items/dsdv_slice_c1x_C__t4/attempt_26 2>/dev/null
ls /srv/opentallas-scratch3/claude/kw26-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items/dsdv_slice_c1x_C__t4/attempt_26 | head
grep -n "work_root" ~/coord/autopilot/kit_wave.json | cut -c1-130 | head
tail -n 400 ~/coord/autopilot/log.txt | grep -a -c "GEN-DISK-LOW"
