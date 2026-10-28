#!/bin/bash
# DIE-KV-5 chain for one die_trial kit: combo GRT TT+FF (DIE-KV-3 grt_run.sh recipe) -> proof (mkproof recipe) ->
# main die_sta_related spice (hb4_dump wrapper, DIE-KV-4 sta_reccal args) -> landed_phase_ocv -> CA spice (ca_spice.py) -> bind v2 relay
# chain.sh TAG
set -e
T=$1; R=/srv/opentallas-scratch2/claude/die-kv-5-1027; K=$R/kit_$T; W=/srv/opentallas-scratch2/claude/wt/die-kv-5/tools
L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128; PL=/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json
LK=/srv/opentallas-scratch2/claude/land-kv-1027
mkdir -p $R/clk$T; cp $K/clock/ctree.v $K/clock/tree.json $R/clk$T/; cp $K/clock/ctree.tcl $R/clk$T/ctree_ck89.tcl
for C in TT FF; do
  mkdir -p $R/out${T}_$C
  CORNER=$C ADJ=0.75 ADJ7=0 python3 $LK/mk_combo_kv.py $K $R/clk$T $R/out${T}_$C
  docker run -d --name dkv5-grt-$T-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $R/out${T}_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
done
for C in TT FF; do docker wait dkv5-grt-$T-$C; docker rm dkv5-grt-$T-$C >/dev/null; grep -E "EXIT|Total overflow|overflow" $R/out${T}_$C/combo_$C.log | tail -n 3; done
mkdir -p $R/proof$T
for C in TT FF; do python3 $LK/trial_tap_arrivals.py $R/clk$T/tree.json $R/out${T}_$C/arr_$C.txt $C $R/proof$T/tap_arrivals_$C.json; done
python3 - $R/clk$T/tree.json $L/land128_regions.json $R/proof$T <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-KV-5: tap table only (no mesh); die_trial link_htree region trees",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
mkdir -p $R/sta$T; cp -r $R/sta_hb4dump/regchar $R/sta$T/
cd $R && python3 $R/hb4_dump.py $W/die_plan $R/sta$T/hb4_pairs_dump.json -- proof$T --plan $PL --out $R/sta$T --clock-cal spice --cppr-lca --clock-ocv table --clock-droop shared --droop-regions $R/proof$T/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 > $R/sta$T.log 2>&1 || echo STA_RC $?
grep -E "intra|seam |DUMP" $R/sta$T.log | cut -c1-260
mkdir -p $R/lpo$T; ln -sfn ../clk$T $R/lpo$T/clk; ln -sfn ../out${T}_TT $R/lpo$T/out_TT; ln -sfn ../out${T}_FF $R/lpo$T/out_FF
python3 $W/s81_head/landed_phase_ocv.py $PL $R/lpo$T --tools $W/die_plan --out $R/lpo$T.json > $R/lpo$T.log 2>&1; echo LPO_RC $?
mkdir -p $R/ca$T; cd $R/ca$T; cp $R/split/ca_spice.py $R/split/count_align_plan.py .
python3 -I ca_spice.py $R/lpo$T.json $L/land128_regions.json ${T}_spice 1.0485 1.0552 --mc 2000 | tail -n 2
python3 -I $R/tools/count_align_bind.py ${T}_spice_xing_lpo.json --from-ocv --parts ocv --scale 1.0 --samples 2000 --out ${T}_spice_bind_parts.json > bind.log 2>&1; echo BIND_RC $?
echo CHAIN_DONE $(date -Is)
