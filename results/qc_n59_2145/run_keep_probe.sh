#!/bin/bash
set -euo pipefail
cd /work
for mode in plain cellkeep; do
 hook=''
 if [ "$mode" = cellkeep ]; then hook='proc; attrmvcp -copy -attr keep;'; fi
 yosys -Q -T -p "read_verilog keep_probe.sv; hierarchy -top keep_probe; $hook synth -top keep_probe -noabc; write_json $mode.json" > "$mode.log"
done
python3 - <<'PY'
import json
for mode in ('plain','cellkeep'):
 d=json.load(open(mode+'.json'))['modules']['keep_probe']; cells=d['cells']; fs=[v for v in cells.values() if 'DFF' in v['type']]
 print(mode, 'physical flops',len(fs), 'a',d['netnames']['a']['bits'],'b',d['netnames']['b']['bits'])
 assert len(fs)==(4 if mode=='plain' else 8)
PY
yosys -Q -T -p 'read_verilog keep_probe.sv; hierarchy -top keep_probe; proc; rename keep_probe gold; read_json cellkeep.json; rename keep_probe gate; miter -equiv -flatten gold gate miter; hierarchy -top miter; async2sync; sat -seq 4 -set-init-zero -prove trigger 0 -verify' > nominal_miter.log
cat > mutant.sv <<'SV'
module mutant(input clk,rst_n,input [3:0] d,output [7:0] q);
wire [7:0] v;
keep_probe u(clk,rst_n,d,v);
assign q=v ^ 8'b1;
endmodule
SV
if yosys -Q -T -p 'read_verilog keep_probe.sv; hierarchy -top keep_probe; proc; rename keep_probe gold; read_json cellkeep.json; read_verilog mutant.sv; miter -equiv -flatten gold mutant miter; hierarchy -top miter; async2sync; sat -seq 4 -set-init-zero -prove trigger 0 -verify' > mutant_miter.log 2>&1; then
 echo 'FAIL: mutant escaped'; exit 1
fi
grep -q 'SAT proof finished - model found: FAIL!' mutant_miter.log
echo 'KEEP_PROBE PASS: eight physical cells, nominal four-cycle miter exact, flipped-output mutant caught'
