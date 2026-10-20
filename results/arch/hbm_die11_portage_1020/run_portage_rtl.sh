#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/claude/codex-hbm-die11-1020/src
python3 - <<'PY'
import gzip,json
A=json.load(gzip.open('../layer.json.gz','rt')); O=json.load(gzip.open('/srv/opentallas-scratch/claude/hbm-die10-1020/planA/artifacts/net/relays_d4g_land.json.gz','rt'));old={b['bus']:b for b in O['relay_splice_v2']}
def cost(b):return sum(len(n['names']) for n in b['nodes'])+sum(len(c) for sk in b['sinks'].values() for c in sk['chain'])
changed=[b for b in A['relay_splice_v2'] if any('_pa' in sk['chain'][-1][0] for sk in b['sinks'].values() if sk['chain'])]
promoted=[b for b in A['relay_splice_v2'] if b['inter_region'] and not old[b['bus']]['inter_region']]
forks=[b for b in A['relay_splice_v2'] if b['inter_region'] and any(len(nd['outs'])>1 for nd in b['nodes'])]
sel={b['bus']:b for b in [min(changed,key=cost),min(promoted,key=cost),min(forks,key=cost)]}
names={n for b in sel.values() for nd in b['nodes'] for n in nd['names']};names|={n for b in sel.values() for sk in b['sinks'].values() for c in sk['chain'] for n in c}
A.update(relay_splice_v2=list(sel.values()),instances=[i for i in A['instances'] if i['name'] in names]);json.dump(A,gzip.open('../rtl_subset.json.gz','wt'));print('RTL_PRODUCTION_SUBSET',list(sel),'instances',len(names))
PY
D=rtl/hbm_accel/die_glue
src=($D/hbfd_rly_fc_masters.sv $D/hbfd_rly_fcf_masters.sv $D/hbfd_rly_masters.sv $D/ot_hbm_rly_fc.sv $D/ot_hbm_rly_fcf.sv $D/ot_hbm_rly.sv rtl/lib/ot_rst_relay.sv $D/hbfd_lane_masters.sv $D/ot_hbm_lane.sv rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv)
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p ../rtl
$VL --version
for m in pos lane_stage bitswap branch_drop land_k; do
 X=(); [ "$m" = pos ] || X=(--mut "$m")
 python3 tools/hbm_die_v16/relay_lockstep_bench.py --layer ../rtl_subset.json.gz --out ../rtl/$m --cycles 160 "${X[@]}"
 $VL --binary --timing -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast --output-split 20000 --output-split-cfuncs 2000 -MAKEFLAGS OPT_FAST=-O1 -MAKEFLAGS OPT_SLOW=-O0 --top-module tb_relay_lockstep -j 8 --Mdir ../rtl/obj_$m -o sim "${src[@]}" ../rtl/$m/tb_relay_lockstep.sv > ../rtl/$m.build.log 2>&1
 ../rtl/obj_$m/sim > ../rtl/$m.run.log 2>&1
 tail -3 ../rtl/$m.run.log
 if [ "$m" = pos ]; then grep -q 'RELAY_LOCKSTEP PASS' ../rtl/$m.run.log; else grep -Eq 'RELAY_LOCKSTEP FAIL checks=[0-9]+ errors=[1-9]' ../rtl/$m.run.log; fi
 echo "$m EXPECTED_VERDICT_PASS"
done
echo PORTAGE_RTL_COHORT_PASS
