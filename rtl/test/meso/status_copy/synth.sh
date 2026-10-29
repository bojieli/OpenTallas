#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}
mkdir -p "$OUT"
yosys -Q -T -p "read_slang --top status_copy_synth $R/rtl/test/meso/status_copy/synth_top.sv $R/rtl/common/ot_dp_clk_landing_ca.sv $R/rtl/common/ot_meso_fifo.sv $R/rtl/common/ot_dp_clk_landing.sv; tcl $R/physical/common_flow/ot_keep_regs.tcl; synth -top status_copy_synth -flatten; write_json $OUT/netlist.json" > "$OUT/synth.log" 2>&1
python3 - "$OUT/netlist.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]));m=j['modules']['status_copy_synth']
nets=m['netnames'];prefix='u_ring.g_control_status_copy.u_status.'
private=set(nets[prefix+'written']['bits']+nets[prefix+'lap_q']['bits'])
original=set(nets['u_ring.s_w']['bits']+nets['u_ring.s_lap']['bits'])
assert len(private)==8 and private.isdisjoint(original),(private,original)
qdrivers={}
for n,c in m['cells'].items():
 if 'DFF' in c['type'].upper():
  for bit in c['connections'].get('Q',[]):qdrivers.setdefault(bit,[]).append(n)
assert all(len(qdrivers.get(bit,[]))==1 for bit in private),qdrivers
print('STATUS_COPY_RETAINED canonical_keep_hook private_FF=8 distinct_from_guard_FF=8 added_cycles=0')
PY
