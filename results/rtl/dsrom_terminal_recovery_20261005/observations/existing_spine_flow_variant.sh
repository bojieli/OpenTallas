#!/bin/bash
set -u
source ~/.opentallas-env
wt=$1
cache=$2
name=$3
out=$4
pq=$5
regions=$6
hold=$7
slew=$8
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 OT_FLOW_TIMEOUT_SECONDS=unlimited OT_SYNTH_TIMEOUT_SECONDS=unlimited
if [ -e "$out" ]; then exit 2; fi
mkdir -p "$out/tmp" "$out/work/orfs/tmp"
export TMPDIR="$out/tmp"
cp "$cache/c${pq}r${regions}.v" "$out/work/orfs/reused_mapped.v"
cd "$wt"
shape=(--core-utilization 35)
if [ "$regions" = 128 ]; then shape=(--die-area 0 0 480 480 --core-area 2.16 2.16 477.84 477.84); fi
python3 tools/run_abi3_physical.py --view asap7 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns --max-fanout 32 --slew-margin-percent "$slew" --hold-margin-ns "$hold" --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 --orfs-var TMPDIR=/work/tmp --orfs-var SYNTH_NETLIST_FILES=/work/reused_mapped.v --keep-heavy-artifacts --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --stages pnr --false-path-io --top ot_v41_pqc_spine_screen --source physical/dsrom_field_spine/ot_v41_pqc_spine_screen.sv --source rtl/v41die/ot_v41_spine_pqc_w17w10.sv --source physical/dsrom_recovery_field/ot_hdc_actquant_screen_stub.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/v41rom/ot_v41_kreg.sv --source rtl/common/ot_prefix.sv --orfs-var 'VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS' --param "PQ=$pq" --param "R=$regions" "${shape[@]}" --nickname-tag "dsfs_$name" --keep-workdir "$out/work" --output "$out/physical.json" > "$out/flow.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$out/flow.exit"
if [ "$rc" -eq 0 ]; then
 python3 - "$out" > "$out/corner_sta.log" 2>&1 <<'STA'
import sys
from tools.w18 import corner_sta as c
original=c.script
def script(corner,base,macros):
 text=original(corner,base,macros)
 check='max' if corner=='ss' else 'min'
 extra='foreach p [get_pins -hierarchical */D] { set s [get_property $p slack_'+check+']; if {$s ne "INF" && $s < 0} { puts "OT_BAD_D_PIN [get_full_name $p] $s" } }\n'
 extra+='report_checks -path_delay '+check+' -group_path_count 100000 -endpoint_path_count 1 -slack_max 0 -format end\n'
 return text.replace('exit\n',extra+'exit\n')
c.script=script
c.main(['--orfs-dir',sys.argv[1]+'/work/orfs','--output',sys.argv[1]+'/corner_sta.json'])
STA
fi
python3 - "$out" "$regions" "$rc" <<'PY'
import json,sys,re
from pathlib import Path
from tools.dsrom_field_spine_route import replicas
out=Path(sys.argv[1]);r=int(sys.argv[2]);rc=int(sys.argv[3]);d=dict(route_rc=rc,verdict='FAIL_FLOW')
if (out/'corner_sta.json').exists() and (out/'physical.json').exists():
 s=json.loads((out/'corner_sta.json').read_text());p=json.loads((out/'physical.json').read_text())['design'];n=next((out/'work/orfs/results/asap7').glob('*/base/6_final.v'));k=replicas(n,r)
 raw={}
 for c in ['ss','ff']:
  t=(out/'work/orfs'/('w18_sta_'+c+'.log')).read_text();m=re.search(r'^OT_WS (\S+)',t,re.M);raw[c]=float(m[1])*1e12 if m else None
 d.update(SS_ps=raw['ss'],FF_ps=raw['ff'],SI=p['signal_integrity_violations'],drc=p['drc'],antenna=p['antenna'],replicas=k,area_um2=p['area_um2'])
 clean=all(d['SI'].get(n)==0 for n in ['max_slew_violations','max_cap_violations','max_fanout_violations']) and d['drc']==0 and d['antenna']==0
 timing=all(raw[c] is not None and raw[c]>=0 for c in ['ss','ff']) and all(s[n]['violating_d_pins']==0 and not s[n]['errors'] for n in ['setup_ss','hold_ff'])
 d['verdict']='PASS_SCREEN_ONLY' if rc==0 and clean and timing and k['passed'] else 'FAIL_PHYSICAL_SCREEN'
(out/'terminal.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d),flush=True)
sys.exit(0 if d['verdict']=='PASS_SCREEN_ONLY' else 1)
PY
terminal_rc=$?
printf '%s\n' "$terminal_rc" > "$out.launch_exit"
exit "$terminal_rc"
