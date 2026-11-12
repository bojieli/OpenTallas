#!/bin/bash
# HBM-HUB-RTL-1 11-11: PRIVATE (DO_NOT_COUNT) two-pass strict bind of t19 with the rd1 recipe: elaborate t11_top_rd1
# (hb_coll_NE/NW VM_RT 4), core_pin_cycles vecd4ae rd1, rd1 hook (main a4c0a585fc + cut guard 3ab5302520).
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
P=/srv/opentallas-scratch2/claude/hbm-cut-1111/rd1d54b; SRC=$P/src; PLAN=$P/plan/die_plan.json; AB=$P/asbuilt_rd1_t19.json
B1=$P/bind_p1; R8=$P/r8; AB2=$P/asbuilt_rd1_t19_p2.json; B2=$P/bind_p2
echo "plan sha $(sha256sum $PLAN | cut -d' ' -f1)  manifest sha $(sha256sum $AB | cut -d' ' -f1)"
cd $SRC || exit 9
rm -rf $B2 $R8; mkdir -p $B1 $R8; touch $B1/DO_NOT_COUNT
[ -s $B1/asbuilt.json ] || { python3 tools/die_plan/bind.py elab $PLAN --out $B1 --asbuilt $AB --mem 48 > $P/elab.log 2>&1; echo "ELAB rc $?"; [ -s $B1/asbuilt.json ] || { tail -20 $P/elab.log; echo ELAB_NOT_OK; exit 11; }; mv $B1/asbuilt.json $B1/asbuilt_elab.json; python3 -I tools/hbm_b2/fused_lower_tree_splice.py splice $B1/asbuilt_elab.json $B1/asbuilt.json $B1/fused_splice_receipt.json || { echo SPLICE_NOT_OK; rm -f $B1/asbuilt.json; exit 12; }; mv $B1/asbuilt.json $B1/asbuilt_spliced.json; python3 -I /srv/opentallas-scratch2/claude/hbm-cut-1111/rd1d54b/fused_close.py /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $B1/asbuilt_spliced.json $B1/asbuilt_closed.json $B1/fused_close_receipt.json || { echo CLOSE_NOT_OK; exit 14; }; python3 -I /srv/opentallas-scratch2/claude/hbm-cut-1111/rd1d54b/prune_dead_latches.py $B1/asbuilt_closed.json $B1/asbuilt_pruned.json || { echo LATCH_NOT_OK; exit 13; }; python3 -I /srv/opentallas-scratch2/claude/hbm-cut-1111/rd1d54b/cache_names.py /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $B1/asbuilt_pruned.json $B1/asbuilt.json $B1/cache_names_receipt.json || { echo NAMES_NOT_OK; rm -f $B1/asbuilt.json; exit 15; }; bash $P/remap3.sh; }
python3 -I -c "import json;m=json.load(open('$B1/asbuilt.json'))['modules'];t=m['hbm_current_native_top']['cells'];[print('ELAB',c,{k:v for k,v in m[t[c]['type']].get('parameter_default_values',{}).items() if k=='VM_RT'},t[c].get('parameters',{}).get('VM_RT')) for c in ('hb_coll_NE','hb_coll_NW','hcollgi_NE')]"
python3 tools/die_plan/bind.py bind $PLAN --out $B1 --asbuilt $AB --mem 48 --strict > $P/bind_p1.log 2>&1; rc=$?
echo "PASS1 rc $rc stale=$(grep -c R8_STALE $P/bind_p1.log) other=$(grep -v R8_STALE $P/bind_p1.log | grep -c -E 'ERROR|^[A-Z_]+ ')"
grep -h 'PARAM_REGEN\|core pin cycles\|FIXED_LATENCY' $P/bind_p1.log | cut -c1-300 | head -12
if [ $rc = 0 ] && python3 -I -c "import json,sys;r=json.load(open('$B1/bind_report.json'));sys.exit(0 if r.get('n_errors',0)==0 else 1)"; then B2=$B1; AB2=$AB; echo "pass 1 clean"
else
  [ -s $B1/bus_groups.json ] || { grep -v R8_STALE $P/bind_p1.log | tail -8 | cut -c1-300; echo BIND_NOT_OK; exit 10; }
  python3 -I -B physical/die_plan/hbm/r8/hbm_lat_pads.py $PLAN $B1/bus_groups.json physical/die_plan/hbm/r8/hbm_lat_contract.json --out $R8 --tools tools/die_plan > $R8/pads.log 2>&1; echo "PADS rc $?"
  T=$(ls $R8/*_r8_landing.json | head -1); [ -s "$T" ] || { tail -5 $R8/pads.log; echo NO_TABLE; echo BIND_NOT_OK; exit 10; }
  python3 -I - $AB $AB2 $T <<PY
import json,sys
d=json.load(open(sys.argv[1])); d["land_r8"]=sys.argv[3]
d["land_r8_note"]=d.get("land_r8_note","")+" | HBM-HUB-RTL-1 11-11 rd1 private: hbm_lat_pads.py re-run on t19 rd1 pass 1"
json.dump(d,open(sys.argv[2],"w"),indent=1)
PY
  rm -rf $B2; mkdir -p $B2; touch $B2/DO_NOT_COUNT; ln -s $B1/asbuilt.json $B2/asbuilt.json
  python3 tools/die_plan/bind.py bind $PLAN --out $B2 --asbuilt $AB2 --mem 48 --strict > $P/bind_p2.log 2>&1 || { echo "BIND2_RC $?"; grep -v R8_STALE $P/bind_p2.log | tail -12 | cut -c1-300; echo BIND_NOT_OK; exit 10; }
fi
python3 -I -c "import json;r=json.load(open('$B2/bind_report.json'));print('BIND',json.dumps({k:r.get(k) for k in ('partitions','crossings','n_errors')}));print('LC',json.dumps(r.get('latency_consumers',{}).get('stats')))"
python3 -I -c "import json;d=json.load(open('$B2/param_regen.json'));rec=d.get('record',{});print('PIN_REGEN',json.dumps(rec.get('core_pin_regen'))[:1500]);ch=[c for c in d.get('changed',[]) if c['param'] in ('VM_RT','BANK_RT','RR_RT','RD_LAT','VM_RT_EXTRA','READ_RETURN','CR_RT')];print('CHANGED',len(ch),json.dumps(ch)[:2500])"
echo BIND_OK
