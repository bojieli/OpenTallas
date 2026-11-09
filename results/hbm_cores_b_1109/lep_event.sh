set -e
C=/srv/opentallas-scratch2/claude/codex-head-ctl-1113; W=/srv/opentallas-scratch2/claude/dh88/lep
mkdir -p $W; du -sh $C/lep_vf_event_v6_reset
SRC=$W/src_v6plusbins; rm -rf $SRC; cp -r $C/lep_vf_event_v6_reset $SRC
cp /srv/opentallas-scratch2/claude/dh88/lep_probe/sink_bins_lep.json $SRC/assets/sink_bins_lep_dt.json
python3 -I - <<P
import json
p="$SRC/source_plan.json"; d=json.load(open(p))
c=d["partition_types"]["hd_lep0N"]["clock"]
c["sink_bins_file"]="$SRC/assets/sink_bins_lep_dt.json"
c["tap_max_sinks"]=1800
json.dump(d,open(p,"w"),indent=1)
P
cat > $W/spec.json <<S
{"entries": {"hd_lep0N": {"radius": 200, "target": 1200}}, "tag": "DIE-HEAD-88 LEP density entries (clk tree 1056 ps FF single entry on 1762x1227)"}
S
cd $C/lep_source/tools/s81_head; python3 head_rf_plan_delta.py $SRC $W/event_dt --spec $W/spec.json --report $W/report.json 2>&1 | tail -20 | cut -c1-300
ls $W/event_dt | head; python3 -I -c "
import json;r=json.load(open('$W/report.json'));print(json.dumps(r)[:1800])"
