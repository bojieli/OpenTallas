#!/bin/bash
# DIE-HBM-101 11-12: HBM event bind of pEv10 (pEv6 + LATCHECK-1 118 fc pricing + q_sm0/q_sm1 as-built symmetry); recipe = bindEv6 (bindR2 strict two-pass, r8, land_r8, kit_source_station_pricing true); tree main 12994e9e691a (LANE_ASBUILT in strict bind). DO_NOT_COUNT
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
D=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane/hbm101/bindEv10
SRC=/srv/opentallas-scratch2/claude/wt/hbm101_main_12994e9e
AB0=$D/asbuilt0.json
PLAN=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane/plans/pEv10/die_plan.json
B1=$D/bind_p1; R8=$D/r8; AB=$D/asbuilt.json; BIND=$D/bind
cd "$SRC" || exit 9
sha256sum "$PLAN" | cut -c1-12
bindrun() { rm -rf "$1"; mkdir -p "$1"; touch "$1/DO_NOT_COUNT"; ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json "$1/asbuilt.json"; python3 tools/die_plan/bind.py bind "$4" --out "$1" --asbuilt "$2" --mem 32 --strict > "$3" 2>&1; }
bindrun "$B1" "$AB0" "$D/bind_p1.log" "$PLAN"; echo "P1 rc $?"
[ -s "$B1/bus_groups.json" ] || { echo NO_BUS_GROUPS; tail -5 "$D/bind_p1.log"; exit 10; }
rm -rf "$R8"; mkdir -p "$R8"
python3 -I -B physical/die_plan/hbm/r8/hbm_lat_pads.py "$PLAN" "$B1/bus_groups.json" physical/die_plan/hbm/r8/hbm_lat_contract.json --out "$R8" --tools tools/die_plan > "$R8/pads.log" 2>&1; echo "PADS rc $?"
T=$(ls "$R8"/*_r8_landing.json | head -1); [ -s "$T" ] || { echo NO_TABLE; tail -5 "$R8/pads.log"; exit 10; }
python3 -I -c "import json,sys;d=json.load(open('$AB0'));d['land_r8']='$T';json.dump(d,open('$AB','w'),indent=1)"
bindrun "$BIND" "$AB" "$D/bind_p2.log" "$PLAN"; echo "P2 rc $?"; tail -5 "$D/bind_p2.log" | cut -c1-300
python3 -I -c "import json,sys;r=json.load(open('$BIND/bind_report.json'));print('BIND',json.dumps({k:r.get(k) for k in ('partitions','crossings','n_errors')}));la=r['lanes']['landing_alignment'];print('stale',la.get('stale'),'uncovered',la.get('uncovered'),'pad_flops',la.get('pad_flops'));e=r.get('errors');print('ERRS',json.dumps(e[:5] if isinstance(e,list) else e)[:1500])"
sha256sum "$BIND/bind_report.json" "$T"; echo BIND_EV10_DONE
W=/srv/opentallas-scratch2/claude/wt/hbm101_main_12994e9e; cd $W && python3 -I tools/die_plan/lane_asbuilt_latency.py $BIND $PLAN --asbuilt $AB --tsv $D/asb.tsv --json $D/asb.json 2>&1 | tail -n 3 | cut -c1-300; echo ASB rc ${PIPESTATUS[0]}
