#!/bin/bash
# HBM-WIRE GEN2b chain (local driver, fleet for every heavy step; branch claude/hbm-wire-1018, chain worktree wt/hd4g-gen2b).
# GEN2b = GEN2 (claude/hd4g-gen2-1018 5b668d464, LAND=1) + l7_wire: cxij_SE/NW/NE INJ_RET 11 -> 9, B39_NOOP 0 -> 1 (the
# inject slot behind the cij join) + gap sync.  Same masters / ports / edges as GEN2 -> no new placement case, stations or
# landing: GEN2b re-uses GEN2's post-landing contract and re-runs only what the 3 parameter changes touch.
#  S0 wait for GEN2 S6 to finish (GEN2 log shows STEP S7, i.e. its relay/landing masters are synthesised) or GEN2 to exit
#  -> S1 l7_wire on GEN2's net/contract.json + strict bind + FUNCTIONAL bind (strict) -> S6 views + SYNTH (only the 3
#  re-parametrised cxij leaves are new) -> S7 GEN2b die case (GEN2's gen_d4g2.sh) -> S8 GRT2b + neighbour-skew gate.
set -o pipefail
W=/home/ubuntu/wt/hd4g-gen2b; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2b; A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1
B=/srv/opentallas-scratch/claude/hd4g/gen2b; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g
step() { echo "STEP $* $(date -Is)"; }
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
H=$(git -C $W rev-parse --short=9 HEAD); echo "HEAD $H"
mkdir -p $A/net $A/pb; cd $W
step S0 wait_gen2_s6
G2PID=$(cat $A2/chain_d4g2.pid 2>/dev/null || echo 1)
while ! grep -q '^STEP S7' $A2/chain_d4g2.log 2>/dev/null && kill -0 $G2PID 2>/dev/null; do sleep 300; done
grep -q '^STEP S7' $A2/chain_d4g2.log || { echo "GEN2B_ABORT: GEN2 exited before S7: $(tail -3 $A2/chain_d4g2.log | tr '\n' ' ')"; exit 10; }
[ -f $A2/net/contract.json ] || { echo GEN2B_ABORT_NO_CONTRACT; exit 10; }
step S1 l7_wire_bind_functional
python3 tools/hbm_die_v16/d4g_layers/l7_wire.py $A2/net/contract.json $A/net/contract.json --report $A/net/l7_wire.json > $A/net/l7.log 2>&1
tail -2 $A/net/l7.log; [ -f $A/net/contract.json ] || { echo S1_L7_FAIL; exit 11; }
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $A/net/contract.json $A/pb > /dev/null; tail -1 $A/pb/port_bind.log
grep -q "^DIE_PORT_BIND PASS" $A/pb/port_bind.log || { echo S1_BIND_FAIL; grep '^FAIL' $A/pb/port_bind.log | head; exit 11; }
python3 tools/hbm_die_v16/d4g_functional_bind.py $A/net/contract.json --report $A/pb/functional_bind.json > $A/pb/functional_bind.log 2>&1
tail -12 $A/pb/functional_bind.log
grep -q "^FUNCTIONAL_BIND PASS" $A/pb/functional_bind.log || { echo S1_FUNCTIONAL_FAIL; exit 11; }
python3 tools/hbm_die_v15/check_contract_modules.py --contract $A/net/contract.json --rev HEAD --json $A/pb/contract_modules_check.json > $A/pb/cmc.log 2>&1; tail -1 $A/pb/cmc.log
synth_round() {   # $1 contract  $2 vplan dir  $3 tag   (as chain_d4g2.sh, metas from GEN0/GEN1/GEN2 + own)
  rm -rf $2; python3 tools/hbm_die_v15/v16_views.py --out $2 --contract $1 | tail -3
  rm -rf $A/synmeta_$3; mkdir -p $A/synmeta_$3
  for P in $A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a/synth $A2/vplan/synth; do [ -d $P ] && (cd $P && tar -cf - */meta.json 2>/dev/null) | tar -x -C $A/synmeta_$3; done
  PREV=$A2/vplan; [ -f $PREV/views.json ] || PREV=$A2/vplan_a
  python3 tools/hbm_die_v16/synth_reuse_r8b.py --views $2 --metas $A/synmeta_$3 --root $W --out $A/reuse_$3.json --prev $PREV > $A/reuse_$3.log; tail -3 $A/reuse_$3.log | cut -c1-600
  CELLS=$(grep '^SYNTH ' $A/reuse_$3.log | cut -d' ' -f2-)
  python3 - $2 > $A/src_paths_$3.txt <<PY
import json, sys
V=json.load(open(sys.argv[1] + '/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/hbm_mtp/rtl','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
print('\n'.join(sorted(p)))
PY
  ssh ot-epyc4 "rm -rf $B/src_$H" || return 15
  git -C $W archive HEAD $(cat $A/src_paths_$3.txt) | ssh ot-epyc4 "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || return 15
  tar -C $2/wrap -cf - . | ssh ot-epyc4 "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || return 15
  for h in ot-agidock128 ot-pve1 ot-epyc5; do ssh ot-epyc4 "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
  echo "SYNTH_$3 $CELLS"
  if [ -n "${CELLS// /}" ]; then
    (cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $2 --commit $H --remote-root $B $CELLS > $A/drive_$3.log 2>&1); tail -2 $A/drive_$3.log
    python3 $W/tools/hbm_die_v15/v16_fetch.py --views $2 --remote-root $B --commit $H --contract $1 $CELLS > $A/fetch_$3.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch_$3.log
    MISS=""; for c in $CELLS; do [ -f $2/synth/$c/meta.json ] || MISS="$MISS $c"; done
    [ -n "$MISS" ] && { echo "SYNTH_MISSING_$3$MISS (no stubs: every SYNTH view needed)"; return 16; }
  fi
  return 0
}
views_up() {      # $1 vplan dir  $2 contract  -> $B/views (GEN0 + GEN1 + GEN2 + GEN2b synth overlays)
  ssh ot-epyc4 "rm -rf $B/views && mkdir -p $B/views/synth" || return 17
  for P in $A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a/synth $A2/vplan/synth $1/synth; do [ -d $P ] && rsync -a $P/ ot-epyc4:$B/views/synth/; done
  scp -q $1/views.json ot-epyc4:$B/views/ && scp -q $2 ot-epyc4:$B/views/contract.json || return 17
}
step S6 views_synth_final
synth_round $A/net/contract.json $A/vplan b || exit $?
python3 tools/hbm_die_v16/d4g_bindings.py --views $A/vplan/views.json --grants $D/grants_d4g.json --out $A/view_bindings.json
step S7 gen2b
views_up $A/vplan $A/net/contract.json || exit 17
scp -q $A2/gen_d4g2.sh ot-epyc4:$B/gen_d4g2.sh || exit 17
$OTRUN --mem 64 --threads 2 --hosts ot-epyc4 --priority die --dir $B -- env OT_ABS_PIN_WINDOW_UM=3 OT_GEN2_CASE=case bash $B/gen_d4g2.sh \
  > $A/gen.otrun 2>&1; echo "GEN ot-run rc=$? $(date -Is)"; tail -20 $A/gen.otrun
grep -q GEN_OK $A/gen.otrun || exit 17
scp -q ot-epyc4:$B/overreach.json ot-epyc4:$B/case/layout.png $A/ 2>/dev/null
step S8 grt2b
$OTRUN --mem 160 --threads 16 --hosts ot-epyc4 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh ot-epyc4 "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log" > $A/grt_summary.txt 2>&1
cat $A/grt_summary.txt
echo CHAIN_D4G2B_DONE
