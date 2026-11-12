#!/bin/bash
# DIE-HBM-100: strict bind of the next HBM plan t31 (d50a + core-shape re-points), two-pass R8 flow.
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
W=/srv/opentallas-scratch2/claude/hbm-cut-1111
SRC=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_fe0002fac6
PLAN=$W/compose/t31/die_plan.json; AB=$W/bind/asbuilt_cut1111_t10.json
B1=$W/bind/bind_t31_p1; R8=$W/bind/r8_t31; AB2=$W/bind/asbuilt_t31.json; B2=$W/bind/bind_t31
echo "plan sha $(sha256sum $PLAN | cut -d" " -f1)"
cd $SRC || exit 9
rm -rf $B1 $B2 $R8; mkdir -p $B1 $R8; touch $B1/DO_NOT_COUNT
ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $B1/asbuilt.json
python3 tools/die_plan/bind.py bind $PLAN --out $B1 --asbuilt $AB --mem 32 --strict > $W/bind/bind_t31_p1.log 2>&1; rc=$?
echo "PASS1 rc $rc stale=$(grep -c R8_STALE $W/bind/bind_t31_p1.log) other=$(grep -v R8_STALE $W/bind/bind_t31_p1.log | grep -c -E "ERROR|^[A-Z_]+ ")"
if [ $rc = 0 ] && python3 -I -c "import json,sys;r=json.load(open(\"$B1/bind_report.json\"));sys.exit(0 if r.get(\"n_errors\",0)==0 else 1)"; then B2=$B1; AB2=$AB; echo "pass 1 clean, no table re-derivation"
else
  [ -s $B1/bus_groups.json ] || { echo NO_BUS_GROUPS; grep -v R8_STALE $W/bind/bind_t31_p1.log | tail -8 | cut -c1-300; echo BIND_NOT_OK; exit 10; }
  python3 -I -B physical/die_plan/hbm/r8/hbm_lat_pads.py $PLAN $B1/bus_groups.json physical/die_plan/hbm/r8/hbm_lat_contract.json --out $R8 --tools tools/die_plan > $R8/pads.log 2>&1; echo "PADS rc $?"; grep "^LOOP" $R8/pads.log | cut -c1-80
  T=$(ls $R8/*_r8_landing.json | head -1); [ -s "$T" ] || { echo NO_TABLE; echo BIND_NOT_OK; exit 10; }
  python3 -I - $AB $AB2 $T <<PY
import json,sys
d=json.load(open(sys.argv[1])); d["land_r8"]=sys.argv[3]
d["land_r8_note"]=d.get("land_r8_note","")+" | DIE-HBM-100 11-11: hbm_lat_pads.py re-run on t31 (d50a + re-points)"
json.dump(d,open(sys.argv[2],"w"),indent=1)
PY
  rm -rf $B2; mkdir -p $B2; touch $B2/DO_NOT_COUNT; ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $B2/asbuilt.json
  python3 tools/die_plan/bind.py bind $PLAN --out $B2 --asbuilt $AB2 --mem 32 --strict > $W/bind/bind_t31_p2.log 2>&1 || { echo "BIND2_RC $?"; grep -c R8_STALE $W/bind/bind_t31_p2.log; grep -v R8_STALE $W/bind/bind_t31_p2.log | tail -10 | cut -c1-300; echo BIND_NOT_OK; exit 10; }
fi
python3 -I -c "import json,sys;r=json.load(open(\"$B2/bind_report.json\"));print(\"BIND\",json.dumps({k:r.get(k) for k in (\"partitions\",\"crossings\",\"n_errors\")}));la=r[\"lanes\"][\"landing_alignment\"];print(\"stale\",la.get(\"stale\"),\"uncovered\",la.get(\"uncovered\"),\"pad_flops\",la.get(\"pad_flops\"));sys.exit(0 if r.get(\"n_errors\",0)==0 else 3)" || { echo BIND_NOT_OK; exit 10; }
touch $B2/.bind_ok; (cd $B2 && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS); sha256sum $B2/SHA256SUMS $B2/bind_report.json $AB2 ${T:-/dev/null}
echo BIND_OK
