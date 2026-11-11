#!/bin/bash
# DIE-HBM-100 11-11: pass 2 of the standard two-pass R8 flow (pass1 = bind_cut.sh: strict bind, R8_STALE only).
# hbm_lat_pads.py (HBM r8 table + fixed-latency loop equalisation) on plan t10 + pass-1 bus_groups, then strict bind with land_r8 -> new table.
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
W=/srv/opentallas-scratch2/claude/hbm-cut-1111
SRC=/srv/opentallas-scratch2/claude/kw43/src_hbm_tc1111p_por36
PLAN=$W/compose/t10/die_plan.json
AB=/srv/opentallas-scratch2/claude/kw43-canon/hbm/asbuilt_p37su5_sm_lat_vK5d_c12.json
B1=$W/bind/bind_cut1111_t10; R8=$W/bind/r8_t10; AB2=$W/bind/asbuilt_cut1111_t10.json; BIND=$W/bind/bind_cut1111_t10_p2
echo "plan sha $(sha256sum $PLAN | cut -d' ' -f1)"
[ -s $B1/bus_groups.json ] || { echo NO_BUS_GROUPS; echo BIND_NOT_OK; exit 9; }
rm -rf $R8; mkdir -p $R8
cd $SRC || exit 9
python3 -I -B physical/die_plan/hbm/r8/hbm_lat_pads.py $PLAN $B1/bus_groups.json physical/die_plan/hbm/r8/hbm_lat_contract.json --out $R8 --tools tools/die_plan > $R8/pads.log 2>&1; echo "PADS rc $?"; tail -3 $R8/pads.log | cut -c1-400
T=$(ls $R8/*_r8_landing.json | head -1); [ -s "$T" ] || { echo NO_TABLE; echo BIND_NOT_OK; exit 10; }
python3 -I - "$AB" "$AB2" "$T" <<PY
import json,sys
d=json.load(open(sys.argv[1])); d["land_r8"]=sys.argv[3]
d["land_r8_note"]=d.get("land_r8_note","")+" | DIE-HBM-100 11-11: hbm_lat_pads.py re-run on the HBM 12:00 cut plan t10 e6bb764f (channels rev3 pin cycles)"
json.dump(d,open(sys.argv[2],"w"),indent=1)
PY
rm -rf "$BIND"; mkdir -p "$BIND"; touch "$BIND/DO_NOT_COUNT"
ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json "$BIND/asbuilt.json"
python3 tools/die_plan/bind.py bind "$PLAN" --out "$BIND" --asbuilt "$AB2" --mem 32 --strict > "$W/bind/bind_p2.log" 2>&1 || { echo "BIND_RC $?"; tail -20 "$W/bind/bind_p2.log" | cut -c1-300; echo BIND_NOT_OK; exit 10; }
python3 -I -c "import json,sys;r=json.load(open(\"$BIND/bind_report.json\"));print(\"BIND\",json.dumps({k:r.get(k) for k in (\"partitions\",\"types\",\"crossings\",\"errors\",\"unbound\",\"n_errors\")}) [:600]);sys.exit(0 if r.get(\"n_errors\",0)==0 else 3)" || { echo BIND_NOT_OK; exit 10; }
touch "$BIND/.bind_ok"
(cd "$BIND" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS); sha256sum "$BIND/SHA256SUMS" "$BIND/bind_report.json" "$T" "$AB2"
echo BIND_OK
