#!/bin/bash
# HBM-VSN-XTAP-2 11-12 t40w = t39w 8b4b6e3071c4 + l3011_dlhbm_1112 (q_hub_nw L3011x2 re-space; step 1, density pass
# pending), DO_NOT_COUNT: strict two-pass bind of t40w on epyc9 against the wave src tree (DIE-HBM-100 COORD priority),
# recipe = bind_t31.sh (src kw45 src_hbm_main_fe0002fac6 + patch_a.py = form A' keys), EQ negative control (bind
# without tap/latch_frac: bound RTL identical) and the diff vs the t31 bind receipt (rtl files + bind_latency.json).
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
D=/srv/opentallas-scratch2/claude/hbm-vsn-xtap-t40w
DB=/srv/opentallas-scratch2/claude/hbm-vsn-xtap-d12b
D12=/srv/opentallas-scratch2/claude/hbm-vsn-xtap-d12
S0=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_fe0002fac6
SRC=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18   # KW-FIX-45 wave src: main 9fc09952cdc4 + q0body guard 0dcd23f1b9c2 + a371160f43 (p18 emit_module); read-only
T31=/srv/opentallas-scratch2/claude/hbm-vsn-xtap-t39w/plan_t39w
AB0=/srv/opentallas-scratch2/claude/hbm-cut-1111/bind/asbuilt_cut1111_t10.json
B31=/srv/opentallas-scratch2/claude/hbm-cut-1111/bind/bind_t37_rx
PD=$D/plan_t40w; PLAN=$PD/die_plan.json
B1=$D/bind_p1; R8=$D/r8; AB=$D/asbuilt_d12b.json; BIND=$D/bind; BNP=$D/bind_nophys
st() { echo "KW_STAGE $1 $(date '+%F %T %Z')"; }
[ "$(sha256sum "$D/die_plan_t40w.json" | cut -c1-12)" = 5129a5aab081 ] || { echo PLAN_SHA_MISMATCH; exit 8; }
[ "$(sha256sum "$T31/die_plan.json" | cut -c1-12)" = 8b4b6e3071c4 ] || { echo T31_SHA_MISMATCH; exit 8; }
if [ ! -f "$PD/.plan_ok" ]; then
  rm -rf "$PD"; cp -al "$T31" "$PD" || exit 9
  rm -f "$PD/die_plan.json" "$PD/die_plan.json.gz" "$PD/g0_report.json" "$PD/g0_base_report.json" "$PD/eq_gate.json"
  cp "$D/die_plan_t40w.json" "$PLAN" && touch "$PD/DO_NOT_COUNT" "$PD/.plan_ok" || exit 9
fi
cd "$SRC" || exit 9
bindrun() {  # $1 out $2 asbuilt $3 log $4 plan
  rm -rf "$1"; mkdir -p "$1"; touch "$1/DO_NOT_COUNT"
  ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json "$1/asbuilt.json"
  python3 tools/die_plan/bind.py bind "$4" --out "$1" --asbuilt "$2" --mem 32 --strict > "$3" 2>&1
}
if [ ! -f "$BIND/.bind_ok" ]; then
  st bind_p1; bindrun "$B1" "$AB0" "$D/bind_p1.log" "$PLAN"; echo "P1 rc $? R8_STALE $(grep -c R8_STALE "$D/bind_p1.log")"
  [ -s "$B1/bus_groups.json" ] || { echo NO_BUS_GROUPS; grep -v R8_STALE "$D/bind_p1.log" | tail -5 | cut -c1-300; exit 10; }
  st r8; rm -rf "$R8"; mkdir -p "$R8"
  python3 -I -B physical/die_plan/hbm/r8/hbm_lat_pads.py "$PLAN" "$B1/bus_groups.json" physical/die_plan/hbm/r8/hbm_lat_contract.json --out "$R8" --tools tools/die_plan > "$R8/pads.log" 2>&1; echo "PADS rc $?"; grep "^LOOP" "$R8/pads.log" | cut -c1-60
  T=$(ls "$R8"/*_r8_landing.json | head -1); [ -s "$T" ] || { echo NO_TABLE; exit 10; }
  python3 -I - "$AB0" "$AB" "$T" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d["land_r8"]=sys.argv[3]
d["land_r8_note"]=d.get("land_r8_note","")+" | HBM-VSN-XTAP-2 11-12: hbm_lat_pads.py re-run on t40w = t39w + l3011_dlhbm_1112"
json.dump(d,open(sys.argv[2],"w"),indent=1)
PY
  st bind_p2; bindrun "$BIND" "$AB" "$D/bind_p2.log" "$PLAN" || { echo "P2 rc $?"; grep -v R8_STALE "$D/bind_p2.log" | tail -10 | cut -c1-300; exit 10; }
  python3 -I -c "import json,sys;r=json.load(open('$BIND/bind_report.json'));print('BIND',json.dumps({k:r.get(k) for k in ('partitions','crossings','n_errors')}));la=r['lanes']['landing_alignment'];print('stale',la.get('stale'),'uncovered',la.get('uncovered'),'pad_flops',la.get('pad_flops'));sys.exit(0 if r['n_errors']==0 else 3)" || exit 10
  touch "$BIND/.bind_ok"
  (cd "$BIND" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS); sha256sum "$BIND/SHA256SUMS" "$BIND/bind_report.json" "$T" "$AB"
fi
if [ ! -f "$BNP/.bind_ok" ]; then
  st bind_nophys; rm -rf $D/plan_nophys; cp -al $PD $D/plan_nophys && rm -f $D/plan_nophys/die_plan.json || exit 10
  python3 -I -c "
import json; d=json.load(open('$PLAN')); lk=d['clock']['ft_hop_lockup']; lk.pop('tap'); lk.pop('latch_frac')
json.dump(d, open('$D/plan_nophys/die_plan.json','w'), indent=1)"
  bindrun "$BNP" "$AB" "$D/bind_nophys.log" "$D/plan_nophys/die_plan.json" || { echo "NOPHYS rc $?"; exit 10; }
  touch "$BNP/.bind_ok"
fi
echo "EQ_CONTROL rtl files $(cd $BIND/rtl && ls | wc -l) diff_vs_nophys $(diff -rq $BIND/rtl $BNP/rtl | wc -l) latency_json_same $(cmp -s $BIND/bind_latency.json $BNP/bind_latency.json && echo 1 || echo 0) names_same $(cmp -s $BIND/bind_names.json $BNP/bind_names.json && echo 1 || echo 0)"
echo "ot_dp_lk insts: $(cat $BIND/rtl/*.sv | grep -c 'ot_dp_lk #')  U_FX: $(cat $BIND/rtl/*.sv | grep -c 'u_fx_')"
echo "P18 emit: __p18bind instances in bound rtl: $(cat $BIND/rtl/*.sv | grep -c 'ot_hbm_su_pg_lane_exp_core__p18bind ') module files: $(grep -l 'module ot_hbm_su_pg_lane_exp_core__p18bind' -r $BIND | wc -l)"
python3 -I - "$BIND" <<'PY'
import json,sys,glob,re
b=sys.argv[1]
for t in ("q_su00","q_su01","q_su10","q_su11"):
    for v in (t,t+"__physical_v1"):
        fs=glob.glob(f"{b}/rtl/*{v}*.sv")
        n=sum(len(re.findall(r"lane_exp_core__p18bind\s",open(f).read())) for f in fs)
        print("LANE_EXP_TYPE",v,"rtl files",len(fs),"p18bind insts",n)
PY
st done; echo BIND_T40W_DONE
