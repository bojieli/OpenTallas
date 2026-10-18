#!/bin/bash
# H-D4G chain gen0 (local driver): S1 src trees on the fleet -> S2 SYNTH of every SYNTH cell -> S3 fetch -> S4 GEN on E4 -> S5 GRT on E4.
set -o pipefail
W=/home/ubuntu/wt/hd4g; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; B=/srv/opentallas-scratch/claude/hd4g/gen0; OTRUN=/home/ubuntu/bin/ot-run
V=$A/vplan
step() { echo "STEP $* $(date -Is)"; }
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
H=$(git -C $W rev-parse --short=9 HEAD); echo "HEAD $H"
step S1 src
python3 - > $A/src_paths.txt <<PY
import json
V=json.load(open('$V/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
print('\n'.join(sorted(p)))
PY
ssh ot-epyc4 "mkdir -p $B && rm -rf $B/src_$H" || exit 11
git -C $W archive HEAD $(cat $A/src_paths.txt) | ssh ot-epyc4 "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || exit 11
tar -C $V/wrap -cf - . | ssh ot-epyc4 "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || exit 11
for h in ot-agidock128 ot-pve1; do ssh ot-epyc4 "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
CELLS=$(python3 -c "import json; V=json.load(open('$V/views.json')); print(' '.join(sorted(c for c,v in V.items() if v['kind']=='SYNTH')))")
step S2 synth $(echo $CELLS | wc -w) cells
cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $V --commit $H --remote-root $B $CELLS > $A/drive.log 2>&1
tail -2 $A/drive.log
step S3 fetch
python3 $W/tools/hbm_die_v15/v16_fetch.py --views $V --remote-root $B --commit $H --contract $A/contract.json $CELLS > $A/fetch.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch.log
MISS=""; for c in $CELLS; do [ -f $V/synth/$c/meta.json ] || MISS="$MISS $c"; done
[ -n "$MISS" ] && echo "SYNTH_MISSING$MISS"
[ -n "$MISS" ] && { echo "S3_FAIL: GEN needs every SYNTH view (no stubs)"; exit 13; }
step S4 gen
ssh ot-epyc4 "rm -rf $B/views && mkdir -p $B/views" && rsync -a $V/synth $V/views.json ot-epyc4:$B/views/ && scp -q $A/contract.json ot-epyc4:$B/views/contract.json \
  && scp -q $A/gen_d4g0.sh ot-epyc4:$B/gen_d4g0.sh || exit 14
$OTRUN --mem 64 --threads 2 --hosts ot-epyc4 --priority die --dir $B -- bash $B/gen_d4g0.sh > $A/gen.otrun 2>&1; echo "GEN ot-run rc=$? $(date -Is)"; tail -20 $A/gen.otrun
grep -q GEN_OK $A/gen.otrun || exit 14
scp -q ot-epyc4:$B/overreach.json ot-epyc4:$B/case/layout.png $A/ 2>/dev/null
ssh ot-epyc4 "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label')}, default=str)[:20000])\"" > $A/gen_manifest_summary.json
step S5 grt
$OTRUN --mem 160 --threads 16 --hosts ot-epyc4 --priority die --dir $B/case -- env CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh ot-epyc4 "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log" > $A/grt_summary.txt 2>&1
cat $A/grt_summary.txt
echo CHAIN_D4G0_DONE
