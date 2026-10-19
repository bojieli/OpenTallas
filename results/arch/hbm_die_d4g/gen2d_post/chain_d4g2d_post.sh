#!/bin/bash
# LH-GEN2CD (LEAD-HBM sub-lane) 10-19 11:45: GEN2d POST-FOREST continuation of resume_forest_codex.sh (Codex durable waiter, source 9d5a2c350).
# The waiter only plans the relay-row reset forest. This script runs everything after it, source-bound to the SAME commit 9d5a2c350
# (worktree wt/hd4g-gen2d-post, branch claude/hd4g-gen2d-post-1019 = 9d5a2c350, contains gen2c b1e9a0734 + 70c8e927e + rstrow 92b6736eb
# + 16 closed _rr records):
#   W0 wait FOREST_RECOVERY_DONE (or waiter exit) -> P0 forest layer present? (else survey + exit 18)
#   S4 splice (d4g_relay_splice) + l12_banklat pads (LAT strict) + strict port bind + functional bind -> S6 synth views -> S7 GEN case (OT_RESET_GATE=fail)
#   -> S8 GRT + STA TT/FF + neighbour-skew clock gate + hold budget (case/run.sh).
# Steps are those of chain_d4g2d.sh (HBM-RSTROW), with: forest from forest_codex9d5a2c350, artifacts under $AP (post/),
# no --hosts pin (data locality via --dir that exists only on ot-epyc4), prior-place = recovered GEN2c case_a run.tcl.
set -o pipefail
W=/home/ubuntu/wt/hd4g-gen2d-post; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d; AP=$A/post; AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c
A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2; A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1
B=/srv/opentallas-scratch/claude/hd4g/gen2d; BC=/srv/opentallas-scratch/claude/hd4g/gen2c; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; HSRC=${HSRC:-15e069307}; FD=${FD:-$A/forest_codex9d5a2c350}; P=$B/forest_codex9d5a2c350
# LH-GEN2CD 11:35: forest_codex9d5a2c350 FAILED (hbm CN: no regional root home within reach after 40 sites). Re-plan variants
# (forest_var/run_var.sh, source 15e069307 = 9d5a2c350 + --max-root-tries + opt-in --overfly-masters, reach unchanged) -> run this with FD=<passing variant dir>.
LANE=/home/ubuntu/claude-takeover-20261007/lanes/LH-GEN2CD.md
step() { echo "STEP $* $(date -Is)"; }
note() { echo "- [LH-GEN2CD chain_d4g2d_post] $(date '+%m-%d %H:%M') $*" >> $LANE; }
mkdir -p $AP/net $AP/pbf; echo $$ > $AP/chain.pid
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
# source binding: every archive / label uses $HSRC; the branch may only add this chain script (results/arch/hbm_die_d4g/gen2d_post/)
H=$HSRC; echo "HEAD $(git -C $W rev-parse --short=9 HEAD) SOURCE $H"
[ -z "$(git -C $W diff --name-only $HSRC HEAD -- . ':!results/arch/hbm_die_d4g/gen2d_post')" ] || { echo "SOURCE_DRIFT vs $HSRC"; exit 9; }
[ -z "$(git -C $W status --porcelain --untracked-files=no -- tools rtl results/arch physical)" ] || { echo DIRTY_WT; exit 9; }
step W0 wait_forest_layer
# FDS: candidate forest dirs (space separated, priority order); the first with a layer wins, give up when all have a report.
FDS=${FDS:-"$A/forest_var/ofly $A/forest_var/ofly57"}
while :; do
  for f in $FDS; do [ -s $f/layer.json.gz ] && { FD=$f; break 2; }; done
  done_all=1; for f in $FDS; do [ -s $f/report.json ] || done_all=0; done
  [ $done_all = 1 ] && { sleep 30; for f in $FDS; do [ -s $f/layer.json.gz ] && { FD=$f; break 2; }; done; FD=${FDS%% *}; break; }
  sleep 60
done
echo "FOREST_DIR $FD"
step P0 forest_layer
if [ ! -s $FD/layer.json.gz ]; then
  echo S4_FOREST_PLAN_FAIL; for f in $FDS; do echo "$f: $(head -c 600 $f/report.json)"; done
  note "S4_FOREST_PLAN_FAIL all variants ($FDS): structural H.RST planner/placement work needed (see reports)"; exit 18
fi
cd $W
step S4 splice_bind
ssh ot-epyc4 "test -s $BC/case_a/run.tcl && cp $BC/case_a/run.tcl $B/prior_run.tcl" || { echo NO_PRIOR_RUN_TCL; exit 9; }
cp $AC/net/contract_pre.json $AP/net/contract_pre.json
python3 tools/hbm_die_v16/d4g_relay_splice.py $AP/net/contract_pre.json $FD/layer.json.gz $AP/net/contract_forest.json --report $AP/net/forest_splice.json \
  > $AP/net/forest_splice.log 2>&1 || { echo S4_FOREST_SPLICE_FAIL; tail -5 $AP/net/forest_splice.log; note "S4_FOREST_SPLICE_FAIL ($AP/net/forest_splice.log)"; exit 18; }
tail -1 $AP/net/forest_splice.log
# l12_banklat LAST (as GEN2e S8b; TW5-BANKLATDIE README: after the forest splice, pads take the endpoint's forest reset). At 9d5a2c350 the
# functional bind's LAT class is STRICT: GEN2c contract_pre alone fails 124 LAT clients (LH-GEN2CD smoke 11:50), so the pads are required.
step S4b l12_banklat
python3 tools/hbm_die_v16/d4g_layers/l12_banklat.py $AP/net/contract_forest.json $AP/net/contract.json --report $AP/net/l12_banklat.json \
  > $AP/net/l12.log 2>&1 || { echo S4B_L12_FAIL; tail -8 $AP/net/l12.log; note "S4B_L12_FAIL ($AP/net/l12.log)"; exit 18; }
tail -2 $AP/net/l12.log
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $AP/net/contract.json $AP/pbf > /dev/null; tail -1 $AP/pbf/port_bind.log
grep -q "^DIE_PORT_BIND PASS" $AP/pbf/port_bind.log || { echo S4_BIND_FAIL; grep '^FAIL' $AP/pbf/port_bind.log | head; note "S4_BIND_FAIL ($AP/pbf/port_bind.log)"; exit 18; }
python3 tools/hbm_die_v16/d4g_functional_bind.py $AP/net/contract.json --report $AP/pbf/functional_bind.json > $AP/pbf/functional_bind.log 2>&1
tail -3 $AP/pbf/functional_bind.log; grep -q "^FUNCTIONAL_BIND PASS" $AP/pbf/functional_bind.log || { echo S4_FUNCTIONAL_FAIL; note "S4_FUNCTIONAL_FAIL ($AP/pbf/functional_bind.log)"; exit 18; }
FOREST_SRC_PATHS="rtl/hbm_accel/die_glue/hbfd_rrl.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_pad.sv rtl/hdc/ot_hdc_delay.sv"
synth_round() {   # $1 contract  $2 vplan dir  $3 tag
  rm -rf $2; python3 tools/hbm_die_v15/v16_views.py --out $2 --contract $1 | tail -3
  rm -rf $AP/synmeta_$3; mkdir -p $AP/synmeta_$3
  for Q in $A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth; do [ -d $Q ] && (cd $Q && tar -cf - */meta.json 2>/dev/null) | tar -x -C $AP/synmeta_$3; done
  python3 tools/hbm_die_v16/synth_reuse_r8b.py --views $2 --metas $AP/synmeta_$3 --root $W --out $AP/reuse_$3.json --prev $AC/vplan_pre > $AP/reuse_$3.log; tail -3 $AP/reuse_$3.log | cut -c1-600
  CELLS=$(grep '^SYNTH ' $AP/reuse_$3.log | cut -d' ' -f2-)
  python3 - $2 > $AP/src_paths_$3.txt <<PY
import json, sys
V=json.load(open(sys.argv[1] + '/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/hbm_mtp/rtl','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016','results/arch/hbm_native_1013/sm_own_logic/retention_cell_models.sv'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
print('\n'.join(sorted(p)))
PY
  (grep -v -e "^#" -e "^ *$" $AC/views/extra_src_paths.txt 2>/dev/null; for x in $FOREST_SRC_PATHS; do echo $x; done) >> $AP/src_paths_$3.txt
  sort -u -o $AP/src_paths_$3.txt $AP/src_paths_$3.txt
  ssh ot-epyc4 "rm -rf $B/src_$H" || return 15
  git -C $W archive $HSRC $(cat $AP/src_paths_$3.txt) | ssh ot-epyc4 "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || return 15
  tar -C $2/wrap -cf - . | ssh ot-epyc4 "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || return 15
  for h in ot-pve1 ot-epyc5; do ssh ot-epyc4 "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
  N0=$(ssh -o ControlPath=none ot-epyc4 "find $B/src_$H | wc -l")
  for h in ot-pve1 ot-epyc5; do n=$(ssh -o ControlPath=none $h "find $B/src_$H 2>/dev/null | wc -l"); echo "SRC $h $n/$N0"
    [ "$n" != "$N0" ] && ssh -o ControlPath=none $h "rm -rf $B/src_$H" && echo "REMOVED_PARTIAL $h"; done
  echo "SYNTH_$3 $CELLS"
  if [ -n "${CELLS// /}" ]; then
    (cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $2 --commit $H --remote-root $B $CELLS > $AP/drive_$3.log 2>&1); tail -2 $AP/drive_$3.log
    python3 $W/tools/hbm_die_v15/v16_fetch.py --views $2 --remote-root $B --commit $H --contract $1 $CELLS > $AP/fetch_$3.log 2>&1; echo "FETCH rc=$?"; tail -3 $AP/fetch_$3.log
    MISS=""; for c in $CELLS; do [ -f $2/synth/$c/meta.json ] || MISS="$MISS $c"; done
    [ -n "$MISS" ] && { echo "SYNTH_MISSING_$3$MISS (no stubs: every SYNTH view needed)"; return 16; }
  fi
  return 0
}
views_up() {
  ssh ot-epyc4 "rm -rf $B/views && mkdir -p $B/views/synth" || return 17
  for Q in $A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth $1/synth; do
    [ -d $Q ] && rsync -a $Q/ ot-epyc4:$B/views/synth/; done
  scp -q $1/views.json ot-epyc4:$B/views/ && scp -q $2 ot-epyc4:$B/views/contract.json || return 17
}
step S6 views_synth_final
synth_round $AP/net/contract.json $AP/vplan d || { rc=$?; note "S6 synth FAIL rc=$rc ($AP/drive_d.log, fetch_d.log)"; exit $rc; }
python3 -c "
import json,collections; v=json.load(open('$AP/vplan/views.json')); print('VIEW_KINDS', dict(collections.Counter(x['kind'] for x in v.values())))"
python3 tools/hbm_die_v16/d4g_bindings.py --views $AP/vplan/views.json --grants $D/grants_d4g.json --out $AP/view_bindings.json
OVR=$(python3 - $AP/vplan/views.json <<'PY'
import json, re, sys, glob
V = json.load(open(sys.argv[1])); out = []
for c, v in sorted(V.items()):
    m = v.get('master', '')
    if v.get('kind') == 'SYNTH' and re.match(r'hbfd_rly_\d+_[A-Z]{2}_rr$', m):
        lef = glob.glob(f'physical/**/views/{m[:-3]}/{m[:-3]}.lef', recursive=True)
        s = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', open(sorted(lef)[0]).read())
        out.append(f'{c}={s.group(1)}x{s.group(2)}')
print(','.join(out))
PY
)
echo "RR_OUTLINE_OVERRIDE ${OVR:-none}"
export OT_DIE_CASE_EXTRA="${OVR:+--outline-override $OVR }--prior-place $B/prior_run.tcl"
step S7 gen2d
views_up $AP/vplan $AP/net/contract.json || exit 17
sed 's#--diagnostic-param-alias#--diagnostic-param-alias ${OT_DIE_CASE_EXTRA}#' $A2/gen_d4g2.sh > $AP/gen_d4g2d.sh
scp -q $AP/gen_d4g2d.sh ot-epyc4:$B/gen_d4g2d.sh && ssh ot-epyc4 "mkdir -p $B/loc_gen_$H" || exit 17
$OTRUN --mem 64 --threads 2 --disk 10 --priority die --dir $B/loc_gen_$H -- env OT_ABS_PIN_WINDOW_UM=3 OT_GEN2_CASE=case OT_RESET_GATE=fail \
  OT_DIE_CASE_EXTRA="$OT_DIE_CASE_EXTRA" bash $B/gen_d4g2d.sh > $AP/gen.otrun 2>&1; echo "GEN ot-run rc=$? $(date -Is)"; tail -20 $AP/gen.otrun
scp -q ot-epyc4:$B/case/layout.png $AP/gen2d_layout.png 2>/dev/null
grep -q GEN_OK $AP/gen.otrun || { note "S7 GEN2d FAIL: $(grep -v '^ot-' $AP/gen.otrun | tail -3 | tr '\n' ' ' | cut -c1-300)"; exit 17; }
scp -q ot-epyc4:$B/overreach.json ot-epyc4:$B/case/placement_coverage.json $AP/ 2>/dev/null
ssh ot-epyc4 "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label','flags')}, default=str)[:20000])\"" > $AP/gen_manifest_summary.json
note "S7 GEN2d GEN_OK -> S8 GRT/STA/CLK launched; LOOK at $AP/gen2d_layout.png"
step S8 grt_sta_clk
$OTRUN --mem 160 --threads 16 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $AP/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh ot-epyc4 "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log; tail -5 $B/case/out/hold_budget.log" > $AP/grt_summary.txt 2>&1
rsync -a ot-epyc4:$B/case/out/ $AP/case_out/ --include='*.json' --include='*.log' --include='*.rpt' --include='*.png' --exclude='*.odb' --exclude='*.def' 2>/dev/null
cat $AP/grt_summary.txt
note "S8 done: $AP/grt_summary.txt (GRT overflow / TT setup / FF hold / neighbour skew) -> classify, update H.GRT/H.STA/H.CLK"
echo CHAIN_D4G2D_POST_DONE HEAD=$H
