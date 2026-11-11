#!/bin/bash
# final.sh NAME : plan_NAME_bf.json -> forward-leg repricing -> latency regen -> G0 + route_supply (traced + stock) + explorer
N=$1; W=/srv/opentallas-scratch3/claude/cpl-kv-pv-3; G=/srv/opentallas-scratch3/claude/cpl-kv-pv-g0/repo; P=physical/die_plan/qwen_kvsys/plan_of_record
RS=/srv/opentallas-scratch2/claude/plan-route-1/watch/tools/die_plan/route_supply.py; RC=/srv/opentallas-scratch2/claude/plan-route-1/release_cache.json
cd $W; exec >> final_$N.log 2>&1; echo "== $(date) final $N"
nice -n 19 python3 -I lat_update.py plan_${N}_bf.json ${N}_rs/station_resite_report.json plan_${N}_fin.json lat_delta_$N.tsv
(cd $G && nice -n 19 python3 -I tools/die_plan/gen.py latency $W/plan_${N}_fin.json --inplace --out $W/lat_$N | tail -1)
md5sum plan_${N}_fin.json; cp plan_${N}_fin.json $G/$P/plan_c_${N}fin.json; cp plan_${N}_fin.json repo/$P/plan_c_${N}fin.json
(cd $G && nice -n 19 python3 -I tools/die_plan/check.py $P/plan_c_${N}fin.json --quiet --out $W/g0f_$N > $W/g0f_$N.log 2>&1) &
for cc in traced stock; do A=""; [ $cc = traced ] && A="--core-conns $W/cc_traced.json"
  (cd repo && nice -n 19 python3 -I $RS --plan $P/plan_c_${N}fin.json --repo . --types kv3_pv_v2,kv3_pv_v4n --release-cache $RC $A --out $W/rsf_${N}_$cc > $W/rsf_${N}_$cc.log 2>&1) & done
for t in kv3_pv_v2 kv3_pv_v4n; do
  (cd repo && nice -n 19 python3 -I /srv/opentallas-scratch3/claude/explorer-script/tools/fleet_viz/explorer_render.py type --plan $P/plan_c_kv1200.json --type $t --repo . --delta $W/delta_kv_pv_$N.json --supply --route-supply $RS --release-cache $RC --out $W/exf_${N}_$t > $W/exf_${N}_$t.log 2>&1) & done
wait
grep "^G0 " g0f_$N.log | cut -c1-90; python3 -I g0diff.py g0x_kv1200/g0_report.json g0f_$N/g0_report.json | head -12
for cc in traced stock; do awk -F'\t' -v c=$cc 'NR>1 && $2 ~ /kv3_pv/ {print "RS",c,$2,$3,$5,$6,$8,"core_H",$12,"street_H",$16,"street_V",$17,"ring_H",$18,"ring_V",$19,"open_H",$20}' rsf_${N}_$cc.log; done
grep -h "after \|before " exf_${N}_*.log | cut -c1-250; echo FINAL_DONE
