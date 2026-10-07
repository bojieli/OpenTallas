#!/bin/bash
# view_hold_eco.sh <src snapshot> <route dir> <master> [eco dir name]   (CLAUDE HBM-ABSTRACTS coordinator, 2026-10-06)
#   Post-detailed-route FF hold ECO (common/post_route_hold_eco.tcl, the hub recipe that closed the HC lane) for a
#   finished route_view.sh die-view route whose only defect is FF hold (SS already >= +40 at sign-off).  The ECO reads
#   6_final.odb + 6_final.sdc + the route's sign-off post-SDCs (POSTSDC, space separated, src-relative; default
#   signoff_unc60 + vclk_corner_true), repairs hold to +HM (default 22) keeping setup margin SM (default 45),
#   re-routes, and writes <route>/<eco> as a route_view.sh-shaped dir: corner_sta.json at the SAME post-SDCs, view/
#   (hbm_fmax_attn_abstract), check.json, physical.json (ECO detailed-route DRC), exit.
set -o pipefail
S=$1; W=$2; M=$3; ED=${4:-eco}
PS=${POSTSDC:-"physical/hbm_accel_die_views/common/signoff_unc60.sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc"}
O=$W/work/orfs; B=$(ls -d $O/results/asap7/*/base); rel=${B#$O/}
E=$W/$ED; EO=$E/work/orfs; EB=$EO/$rel
rm -rf $E; mkdir -p $EB $EO/logs
cp $B/6_final.sdc $EB/; cp $W/args $E/ 2>/dev/null; cat $S/SOURCE_COMMIT > $E/SOURCE_COMMIT
for f in $(ls $B | grep -E '\.(odb|sdc|v|spef)$' | grep -v 6_final); do :; done
PSD=""; for p in $PS; do PSD="$PSD /src/$p"; done
docker run --rm -v $B:/in:ro -v $EB:/out -v $S:/src:ro \
  -e OT_IN=/in -e OT_OUT=/out -e OT_POST_SDC="${PSD# }" -e OT_HOLD_MARGIN=${HM:-22} -e OT_SETUP_MARGIN=${SM:-45} \
  -e OT_KEEP_CLOCK=${KEEPCLK:-0} -e OT_THREADS=${THREADS:-8} -e OT_MAXL=${MAXL:-M7} -e OT_MAX_BUF_PCT=${BUF:-10} ${IMG:-openroad/orfs:asap7lock} bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/physical/hbm_accel_die_views/common/post_route_hold_eco.tcl" \
  > $E/eco.log 2>&1
rc=$?; grep -q "OT_ECO done" $E/eco.log || rc=9
echo "rc=$rc" > $E/exit
cd $S
python3 tools/w18/corner_sta.py $(for p in $PS; do echo -n " --post-sdc $p"; done) --orfs-dir $EO --output $E/corner_sta.json > $E/corner.log 2>&1; echo "corner_rc=$?" >> $E/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $EO --name $M --out $E/view --tmp-dir $E/abs_tmp > $E/export.log 2>&1; echo "export_rc=$?" >> $E/exit
python3 tools/hbm_die_views.py check --master $M --lef $E/view/$M.lef > $E/check.json 2>&1; echo "check_rc=$?" >> $E/exit
python3 - $W $E <<'PY'
import json, re, sys
w, e = sys.argv[1:]
log = open(f'{e}/eco.log').read()
nv = re.findall(r'Number of violations = (\d+)', log)
drc = int(nv[-1]) if nv else None
p = json.load(open(f'{w}/physical.json'))
for c in (p.get('acceptance') or {}).get('checks') or []:
    if c.get('stage') == 'place_and_route':
        c['drc_errors_pre_eco'] = c.get('drc_errors'); c['drc_errors'] = drc
add = re.findall(r'OT_ECO cells_added (-?\d+)', log)
p['post_route_hold_eco'] = dict(script='physical/hbm_accel_die_views/common/post_route_hold_eco.tcl', drc_violations=drc,
                                cells_added=int(add[0]) if add else None,
                                slack_lines=[l for l in log.splitlines() if l.startswith(('OT_ECO', 'worst slack'))][:16])
json.dump(p, open(f'{e}/physical.json', 'w'), indent=1)
PY
for f in SOURCE_COMMIT; do :; done
echo "signoff_export eco_done" >> $E/exit
