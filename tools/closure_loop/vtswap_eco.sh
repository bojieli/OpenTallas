#!/bin/bash
# closure-loop VT-SWAP SETUP ECO stage (eco-sweep 2026-10-09; cwd = the job's src snapshot).  A post-route setup repair
# for THIN TT misses with FF hold >= 0: RVT -> LVT master swaps on the TT-violating paths (vtswap_eco.tcl), capped at
# CAP_PCT % LVT (owner Vt policy 2026-10-07: <= ~2 %), with an FF hold guard.  No re-route (R/L footprints identical), so
# the route's DRC count stands (DRC0) and the routed SPEF is kept.  Output layout = hold_eco.sh's, so the loop's ECO
# completion (result.json -> eco_passes -> eco_install_cmd -> re-verdict -> commit) installs and records it unchanged.
#   vtswap_eco.sh <route base (6_final.odb)> <sign-off base (SDC_NAME)> <out dir> <block> [post-SDC (src-rel)...]
# env: TARGET (TT setup target ps, 10), CAP_PCT (2.0), ROUNDS (60), BAND (4: per round only paths within BAND ps of the worst), HOLD_FLOOR (2), DRC0 (the route's DRC count, required),
#      SDC_NAME (6_final.sdc), SETUP_POST_SDC, MACROS, THREADS (8), ACC_SS / ACC_FF (0 / 0),
#      ORFS_W18 (the route's ORFS dir: on a passing result its w18_sta_{ss,ff}.tcl gain the LVT libraries/LEF, so the
#      loop's routed-insertion re-STA (meas_resta.py) can time the installed db; harmless on an RVT db; originals kept
#      as *.pre_vtswap)
set -eo pipefail
RB=$1; OB=$2; OUT=$3; BLK=$4; shift 4
D=$(basename $(dirname $RB))
CLD=$(cd $(dirname $0) && pwd)
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
[ ! -e "$OUT" ] || { echo "ECO output already exists; preserving evidence: $OUT"; exit 10; }
[ -n "${DRC0:-}" ] || { echo "DRC0 (route DRC count) required"; exit 2; }
mkdir -p "$OUT"
export SDC_NAME=${SDC_NAME:-6_final.sdc}
[ -f "$OB/$SDC_NAME" ] || { echo "sign-off SDC $OB/$SDC_NAME missing"; exit 2; }
DB=6_final.odb; [ -f $RB/$DB ] || { echo "no $RB/$DB"; exit 2; }
SPEF=$OB/6_final.spef; [ -f $SPEF ] || SPEF=$RB/6_final.spef
PS=""; for p in "$@"; do PS="$PS /src/$p"; done
SPS=""; for p in ${SETUP_POST_SDC:-}; do SPS="$SPS /src/$p"; done
MS=""; for m in ${MACROS:-}; do MS="$MS /src/$m"; done
CS_ARGS=$(for p in "$@"; do echo -n " --post-sdc $p"; done; for m in ${MACROS:-}; do echo -n " --macro $m"; done)
SN=""; grep -q -- "--sdc-name" tools/w18/corner_sta.py && SN="--sdc-name $SDC_NAME"
ACC_SS=${ACC_SS:-0}; ACC_FF=${ACC_FF:-0}
P=$OUT/pass1; EB=$P/orfs/results/asap7/$D/base; mkdir -p $EB
cp "$OB/$SDC_NAME" "$EB/6_final.sdc"; [ "$SDC_NAME" = 6_final.sdc ] || cp "$OB/$SDC_NAME" "$EB/$SDC_NAME"
orun() {
  local log=$1 tcl=$2; shift 2
  docker run --rm -v $RB:/in:ro -v $(dirname $SPEF):/inspef:ro -v $OB:/ob:ro -v $P:/p -v $PWD:/src:ro -v $CLD:/cl:ro \
    -e OT_MACROS="${MS# }" -e OT_VT="RVT LVT" -e OT_CL=/cl -e OT_SETUP_LIB=${SETUP_LIB:-TT} "$@" $IMG bash -lc \
    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /cl/$tcl" > $log 2>&1
}
echo "OT_VTSWAP input $RB/$DB spef $SPEF target ${TARGET:-10} cap ${CAP_PCT:-2.0}% drc0 $DRC0" | tee -a $OUT/eco.log
for c in ss ff; do
  CPS="$PS"; [ $c = ss ] && CPS="$PS$SPS"
  orun $P/corner_$c.log hold_eco_corner.tcl -e OT_CORNER=$c -e OT_DB=/in/$DB -e OT_SDC=/ob/$SDC_NAME \
    -e OT_SPEF=/inspef/$(basename $SPEF) -e OT_POST_SDC="${CPS# }" -e OT_EFF=/p/eff_$c.sdc -e OT_CRIT_PS=60
  grep -q "OT_CORNER_EFF done" $P/corner_$c.log || { echo "corner $c session failed"; tail -20 $P/corner_$c.log; exit 9; }
done
{ cat $P/eff_ss.sdc; echo 'set_false_path -hold -to [all_clocks]'; } > $P/mode_ss.sdc
{ cat $P/eff_ff.sdc; echo 'set_false_path -setup -to [all_clocks]'; } > $P/mode_ff.sdc
orun $P/eco_vtswap.log vtswap_eco.tcl -e OT_DB=/in/$DB -e OT_SDC_SS=/p/mode_ss.sdc -e OT_SDC_FF=/p/mode_ff.sdc \
  -e OT_SPEF=/inspef/$(basename $SPEF) -e OT_OUT=/p/orfs/results/asap7/$D/base -e OT_TARGET=${TARGET:-10} \
  -e OT_CAP_PCT=${CAP_PCT:-2.0} -e OT_ROUNDS=${ROUNDS:-60} -e OT_BAND=${BAND:-4} -e OT_HOLD_FLOOR=${HOLD_FLOOR:-2} -e OT_THREADS=${THREADS:-8} || true
cat $P/eco_vtswap.log | grep -v "^\[WARNING STA-1212\]" >> $OUT/eco.log
grep -q "OT_ECO done" $P/eco_vtswap.log || { echo "VT-swap pass failed (no OT_ECO done)"; tail -30 $P/eco_vtswap.log; exit 9; }
cp $SPEF $EB/6_final.spef
python3 tools/w18/corner_sta.py $CS_ARGS $SN --orfs-dir $P/orfs --output $P/corner_sta.json > $P/corner.log 2>&1 \
  || { echo "corner_sta failed"; tail $P/corner.log; exit 8; }
if [ -n "${SETUP_POST_SDC:-}" ]; then
  python3 tools/w18/corner_sta.py $CS_ARGS $(for q in $SETUP_POST_SDC; do echo -n " --post-sdc $q"; done) $SN \
    --orfs-dir $P/orfs --output $P/corner_sta_setup_post.json > $P/corner_setup_post.log 2>&1 \
    || { echo "setup post-SDC corner_sta failed"; tail $P/corner_setup_post.log; exit 8; }
  cp $P/corner_sta.json $P/corner_sta_hold_model.json
  python3 -c "import json,sys; b=json.load(open(sys.argv[1])); p=json.load(open(sys.argv[2]))
for k in ('setup_tt', 'setup_ss'):
    if k in p: b[k] = p[k]
b['setup_post_sdc'] = p['post_sdc']; json.dump(b, open(sys.argv[1], 'w'), indent=1)" $P/corner_sta.json $P/corner_sta_setup_post.json
fi
python3 -c "import json,sys; sys.exit(0 if 'setup_tt' in json.load(open('$P/corner_sta.json')) else 1)" \
  || { echo "corner_sta without setup_tt (pre option-B snapshot): not supported by the VT-swap ECO"; exit 8; }
python3 - $P $ACC_SS $ACC_FF $DRC0 <<'PY'
import json, os, re, sys
p, acc_ss, acc_ff, drc0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
log = open(f'{p}/eco_vtswap.log').read()
cs = json.load(open(f'{p}/corner_sta.json'))
post = re.findall(r'^OT_VTSWAP post tt (\S+) ff (\S+) vt (.*) lvt_pct (\S+) swapped (\d+) frozen (\d+) capped (\d+)', log, re.M)
pre = re.findall(r'^OT_VTSWAP pre tt (\S+) ff (\S+) vt (.*) lvt_pct (\S+)', log, re.M)
su = cs['setup_tt']
r = dict(ss_ps=su['worst_slack_ps'], tt_ps=su['worst_slack_ps'], ff_ps=cs['hold_ff']['worst_slack_ps'], drc=drc0,
         drc_basis='route DRC: a VT master swap moves no pin, wire or DRC shape (ASAP7 R/L LEFs differ only in the implant OBS)',
         sdc_name=os.environ.get('SDC_NAME', '6_final.sdc'), setup_post_sdc=list(cs.get('setup_post_sdc') or []),
         setup_corner=su.get('corner', 'tt'), ss_sensitivity_ps=(cs.get('setup_ss') or {}).get('worst_slack_ps'),
         cells_added=0, errors=su.get('errors', []) + cs['hold_ff'].get('errors', []), session='vtswap', **{'pass': 1})
if post:
    t, f, vt, pct, n, fr, cap = post[-1]
    r.update(lvt_pct=float(pct), lvt_swapped=int(n), hold_frozen=int(fr), lvt_capped=bool(int(cap)), vt_counts=vt,
             session_tt=float(t), session_ff=float(f))
if pre:
    r['pre_session'] = dict(tt=float(pre[-1][0]), ff=float(pre[-1][1]), vt=pre[-1][2], lvt_pct=float(pre[-1][3]))
cap = float(os.environ.get('CAP_PCT', '2.0'))
if r.get('lvt_pct') is not None and r['lvt_pct'] > cap + 1e-9:
    r['errors'].append(f"LVT {r['lvt_pct']:.3f} % over the {cap} % cap")
ok = r['ss_ps'] is not None and r['ff_ps'] is not None
r['score'] = min(r['ss_ps'] - acc_ss, r['ff_ps'] - acc_ff) if ok and r['drc'] == 0 and not r['errors'] else -1e9
json.dump(r, open(f'{p}/result.json', 'w'), indent=1); print('OT_PASS_RESULT', json.dumps(r))
PY
cat $P/result.json >> $OUT/eco.log
ln -sfn pass1/orfs $OUT/orfs
cp $P/corner_sta.json $OUT/corner_sta.json
cp $P/result.json $OUT/result.json
if [ -n "${ORFS_W18:-}" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open('$OUT/result.json'))['score'] >= 0 else 1)"; then
  for c in ss ff; do
    t=$ORFS_W18/w18_sta_$c.tcl; [ -f $t ] || continue
    [ -f $t.pre_vtswap ] || cp $t $t.pre_vtswap
    python3 - $t <<'PY'
import re, sys
t = sys.argv[1]; P = "/OpenROAD-flow-scripts/flow/platforms/asap7"
out = []
for line in open(t).read().splitlines():
    m = re.match(rf"read_liberty ({re.escape(P)}/lib/NLDM/asap7sc7p5t_\w+?)_RVT_(SS|FF|TT)_(\S+)$", line)
    out.append(line)
    if m:
        out.append(f"read_liberty {m.group(1)}_LVT_{m.group(2)}_{m.group(3)}")
    if line.startswith("read_lef ") and "asap7sc7p5t_28_R_1x" in line:
        out.append(line.replace("_28_R_1x", "_28_L_1x"))
open(t, "w").write("\n".join(out) + "\n")
PY
    echo "OT_VTSWAP w18 LVT libraries added: $t (original $t.pre_vtswap)" | tee -a $OUT/eco.log
  done
fi
echo "OT_ECO chosen pass1" | tee -a $OUT/eco.log
cat $OUT/result.json
