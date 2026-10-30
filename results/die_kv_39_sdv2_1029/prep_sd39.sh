#!/bin/bash
# DIE-KV-39 V2 plan prep (intel1): event28b -> main serdes delta -> sd39 clock/reset delta -> mk_sd36 collector regen
set -euo pipefail
WT=/srv/opentallas-scratch2/claude/wt/die-kv-39-sdv2; R=results/die_kv_39_sdv2_1029; D=/srv/opentallas-scratch2/claude/die-kv-39-1029/sdv2
B=/srv/opentallas-scratch2/claude/die-kv-37-1029/bindroot37
cd $WT; git show origin/main:results/die_kv_32_1029/serdes/apply_serdes_phys.py > $D/apply_serdes_phys.py
git show origin/main:results/die_kv_32_1029/serdes/serdes_phys_delta.json > $D/serdes_phys_delta.json
zcat $B/results/die_kv_36_1029/kv021b/event28b_plan.json.gz > $D/event28b_plan.json 2>/dev/null || cp $B/kv36/event28b/plan.json $D/event28b_plan.json
python3 $D/apply_serdes_phys.py tools/die_plan $D/event28b_plan.json $D/serdes_phys_delta.json $D/plan_s.json | tee $D/apply_serdes.log
K=$B/kv39; mkdir -p $K $WT/kv39; cp $R/sd39_bins_*.json $K/; cp $R/sd39_bins_*.json $WT/kv39/; ln -sfn ../kv36/event28b/event27 $K/event27
python3 $R/mk_sd39.py tools/die_plan $D/plan_s.json $K/plan_sd39.json x x kv39/sd39_bins_kv3_sys_SD.json kv39/sd39_bins_kv3_sys_SD_v1.json > $R/sd39_delta.json
python3 $R/check_sd39.py tools/die_plan $K/plan_sd39.json > $R/sd39_check.json
python3 results/die_kv_36_sd_1029/mk_sd36.py tools/die_plan $B/kv36/eB_sidecar.json $K/sidecar_sd39.json $K/plan_sd39.json $K/plan_sd39c.json > $R/sd39_collector.json
python3 - <<PY
import json
d=json.load(open("$R/sd39_check.json"))
for k,v in d.items(): print(k, [(t['name'],t['load'],t['far_um']) for t in v['taps']] if 'taps' in v else v.get('taps_error'), {x:y for x,y in (v.get('reset') or {"err":v.get('reset_error')}).items() if x!='taps'})
c=json.load(open("$R/sd39_collector.json"))
for k,v in c["types"].items(): print(k, v["new_relays"], v["new_relays_on_macro"], v["new_depth"], v["collector_path_max_hop_um"], v["collector_path_on_macro"], [s["hop_um"] for s in v["sources"]])
PY
