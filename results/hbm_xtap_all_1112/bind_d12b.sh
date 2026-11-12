#!/bin/bash
# HBM-VSN-XTAP-2 11-12 d12b A/B split (DIE-HBM-100), DO_NOT_COUNT: strict two-pass bind of plan d12 =
# d53b/t31 ad080c302a2b + d12_formAp_all_types_1112 (69 types on ft_hop_lockup, xtap_flop removed, tap/latch_frac),
# recipe = bind_t31.sh (src kw45 src_hbm_main_fe0002fac6 + patch_a.py = form A' keys), EQ negative control (bind
# without tap/latch_frac: bound RTL identical) and the diff vs the t31 bind receipt (rtl files + bind_latency.json).
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
D=/srv/opentallas-scratch2/claude/hbm-vsn-xtap-d12b
D12=/srv/opentallas-scratch2/claude/hbm-vsn-xtap-d12
S0=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_fe0002fac6
SRC=$D/src_d12b
T31=/srv/opentallas-scratch2/claude/hbm-cut-1111/compose/t31
AB0=/srv/opentallas-scratch2/claude/hbm-cut-1111/bind/asbuilt_t31.json
B31=/srv/opentallas-scratch2/claude/hbm-cut-1111/bind/bind_t31
PD=$D/plan_d12b; PLAN=$PD/die_plan.json
B1=$D/bind_p1; R8=$D/r8; AB=$D/asbuilt_d12b.json; BIND=$D/bind; BNP=$D/bind_nophys
st() { echo "KW_STAGE $1 $(date '+%F %T %Z')"; }
[ "$(sha256sum "$D/die_plan_d12b.json" | cut -c1-12)" = f5b19fb16f74 ] || { echo PLAN_SHA_MISMATCH; exit 8; }
[ "$(sha256sum "$T31/die_plan.json" | cut -c1-12)" = ad080c302a2b ] || { echo T31_SHA_MISMATCH; exit 8; }
if [ ! -f "$PD/.plan_ok" ]; then
  rm -rf "$PD"; cp -al "$T31" "$PD" || exit 9
  rm -f "$PD/die_plan.json" "$PD/die_plan.json.gz" "$PD/g0_report.json" "$PD/g0_base_report.json" "$PD/eq_gate.json"
  cp "$D/die_plan_d12b.json" "$PLAN" && touch "$PD/DO_NOT_COUNT" "$PD/.plan_ok" || exit 9
fi
if [ ! -f "$SRC/.src_ok" ]; then
  st src; [ -d "$SRC" ] && find "$SRC" -type d ! -perm -u+w -exec chmod u+w {} +; rm -rf "$SRC"; cp -al "$S0" "$SRC" || exit 9
  find "$SRC/tools" -type d -exec chmod u+w {} +; rm -rf "$SRC/tools/die_plan"; [ ! -e "$SRC/tools/die_plan" ] || exit 9
  cp -a "$S0/tools/die_plan" "$SRC/tools/die_plan" || exit 9
  python3 -I "$D12/patch_a.py" "$SRC/tools/die_plan" || exit 9
  python3 -I "$D12/patch_hops.py" "$SRC" || exit 9
  touch "$SRC/.src_ok"
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
d["land_r8_note"]=d.get("land_r8_note","")+" | HBM-VSN-XTAP-2 11-12: hbm_lat_pads.py re-run on d12b = d53b + d12b_formAp_ab (xtap_flop removed, A/B)"
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
echo "VS_D12 sv differing: $(diff -rq $BIND/rtl $D12/bind/rtl | grep -c "\.sv ")"; diff -rq $BIND/rtl $D12/bind/rtl | grep "\.sv " | sed "s/.*rtl\///; s/ and .*//" | sort > $D/rtl_diff_vs_d12.txt
echo "VS_T31 rtl files differing: $(diff -rq $BIND/rtl $B31/rtl | wc -l)"
diff -rq $BIND/rtl $B31/rtl | sed 's/.*rtl\///; s/ and .*//' | sort > $D/rtl_diff_vs_t31.txt
echo "U_FX in bound rtl: $(cat $BIND/rtl/*.sv | grep -c 'u_fx_') ot_dp_lk insts: $(cat $BIND/rtl/*.sv | grep -c 'ot_dp_lk #') (t31: $(cat $B31/rtl/*.sv | grep -c 'ot_dp_lk #'))"
python3 -I - "$BIND/bind_latency.json" "$B31/bind_latency.json" <<'PY'
import json,sys
a,b=json.load(open(sys.argv[1])),json.load(open(sys.argv[2]))
def flat(o,p=()):
    if isinstance(o,dict):
        for k,v in o.items(): yield from flat(v,p+(k,))
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from flat(v,p+(i,))
    else: yield p,o
fa,fb=dict(flat(a)),dict(flat(b))
d=[k for k in set(fa)|set(fb) if fa.get(k)!=fb.get(k)]
print("LATENCY_JSON leaves differing vs t31:",len(d)); [print("  ",k,fb.get(k),"->",fa.get(k)) for k in sorted(d,key=str)[:12]]
PY
st done; echo BIND_D12B_DONE
