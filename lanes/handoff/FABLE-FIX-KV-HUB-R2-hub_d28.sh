#!/bin/bash
# FABLE-FIX-KV-HUB-R2 D28 hub ring rows: private tree_h = tree_b (D27d + hroot variant B, plan 9ec33fa3c347) + 9 hard ring cores on
# kv3_hub_Wo and on kv3_hub_Eo (ana/d28_final rows), then the KV-HUBWO-RESET chain by fixed tools: landing_remap resel ->
# collector_reattach --sidecar -> hard_ring_wreg, then G0.  The strict bind + LATCHECK is a separate unit (bind_h.sh).
set -euo pipefail
W=/srv/opentallas-scratch2/claude/fable-fix-kv-hub; SRC=$W/tree_b; T=$W/tree_h; RT=/srv/opentallas-scratch2/claude/rt/4e46a7ec46c5; L=$W/launch_h
P=physical/die_plan/qwen_kvsys/plan_of_record; D=$W/ana/d28_final; O=$W/hub_d28; mkdir -p $O/plans $O/tmp
export PYTHONDONTWRITEBYTECODE=1 OT_HCPARAM_ALL=1 OT_KV_HEAD_KST=2 TMPDIR=$O/tmp
if [ ! -e $T ]; then
  cp -al $SRC $T.tmp
  chmod u+w $T.tmp/$P
  n=0; while IFS= read -r -d '' f; do cp -p "$f" "$f.ffkh" && mv "$f.ffkh" "$f"; n=$((n+1)); done < <(find $T.tmp/$P -maxdepth 1 -type f -links +1 -print0)
  mkdir -p $W/aside_h
  for d in bind_of_record bind_of_record.a_linked bind_of_record.b1_cancelled; do [ -e $T.tmp/$P/$d ] && mv $T.tmp/$P/$d $W/aside_h/$d; done
  cp -a $T.tmp/$P/bind_of_record.d27d_linked $T.tmp/$P/bind_of_record
  mv $T.tmp $T
  echo SETUP_DONE priv $n $(date -u +%T)
fi
[ -e $L ] || bash $RT/tools/autopilot/rt_launch_tree.sh $T $RT $L
cat $L/.rt_launch_ok; echo
test $(sha256sum $T/$P/plan_c.json | cut -c1-12) = 9ec33fa3c347
cp -p $T/$P/plan_c.json $O/plans/plan_base.json; cp -p $T/$P/eW_sidecar.json $O/plans/eW_sidecar_base.json
python3 -I - $O/plans/plan_base.json $O/plans/plan_p0.json $D/rows_kv3_hub_Wo_d28.json $D/rows_kv3_hub_Eo_d28.json <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
for f in sys.argv[3:]:
    r=json.load(open(f)); hc=p["partition_types"][r["type"]]["hard_cores"]
    have={h["inst"] for h in hc}|{h.get("physical_inst") for h in hc}
    for x in r["add_hard_cores"]:
        assert x["inst"] not in have and x["physical_inst"] not in have, x["inst"]
        hc.append(x)
    print("ROWS",r["type"],len(r["add_hard_cores"]),"hard_cores now",len(hc))
p["note"]=p.get("note","")+" | KV-D28-HUBRING (FABLE-FIX-KV-HUB-R2 11-21): kv3_hub_Wo and kv3_hub_Eo +9 hard ring cores each (signed CLAND-MACRO-1 masters)"
json.dump(p,open(sys.argv[2],"w"),indent=1)
PY
cd $L
python3 -I -B tools/die_plan/landing_remap.py $O/plans/plan_base.json $O/plans/plan_p0.json $O/plans/plan_p1.json --types kv3_hub_Wo,kv3_hub_Eo --resets resel \
  --receipt $O/s1_remap_receipt.json > $O/s1_remap.log 2>&1 && echo RC_S1 0 || { echo RC_S1 FAIL; tail -5 $O/s1_remap.log; exit 3; }
python3 -I -B tools/die_plan/collector_reattach.py $O/plans/plan_base.json $O/plans/plan_p1.json $O/plans/plan_p2.json $O/s2_reattach.json \
  --sidecar $O/plans/eW_sidecar_base.json $O/plans/eW_sidecar_p2.json > $O/s2_reattach.log 2>&1 && echo RC_S2 0 || { echo RC_S2 FAIL; tail -5 $O/s2_reattach.log; exit 4; }
python3 -I /srv/opentallas-scratch2/claude/kv-hubwo-reset/hard_ring_wreg.py $O/plans/plan_p2.json $O/plans/plan_p3a.json kv3_hub_Wo $O/s3_wreg_Wo.json
python3 -I /srv/opentallas-scratch2/claude/kv-hubwo-reset/hard_ring_wreg.py $O/plans/plan_p3a.json $O/plans/plan_p3.json kv3_hub_Eo $O/s3_wreg_Eo.json
cp -p $O/plans/plan_p3.json $T/$P/plan_c.json.ffkh && mv $T/$P/plan_c.json.ffkh $T/$P/plan_c.json
[ -s $O/plans/eW_sidecar_p2.json ] && { cp -p $O/plans/eW_sidecar_p2.json $T/$P/eW_sidecar.json.ffkh && mv $T/$P/eW_sidecar.json.ffkh $T/$P/eW_sidecar.json; }
sha256sum $O/plans/* | cut -c1-12,65- ; tail -2 $O/s1_remap.log | cut -c1-300; tail -2 $O/s2_reattach.log | cut -c1-300
echo CHAIN_DONE plan $(sha256sum $T/$P/plan_c.json | cut -c1-12) sidecar $(sha256sum $T/$P/eW_sidecar.json | cut -c1-12)
bash /srv/opentallas-scratch2/claude/kv-plan-r3/d27c/gate_g0_d26.sh $L $O/g0gate || true
tail -3 $O/g0gate/gate.out | cut -c1-400
echo HUB_D28_DONE
