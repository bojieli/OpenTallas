#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for mode in old fixed; do
 cat > "$mode.tcl" <<EOF
yosys read_verilog -sv fixture.sv
EOF
 if [ "$mode" = fixed ]; then echo 'source ot_keep_regs.tcl' >> "$mode.tcl";fi
 cat >> "$mode.tcl" <<EOF
yosys synth -top keep_hc
yosys write_json $mode.json
EOF
 yosys -Q -T -c "$mode.tcl" > "$mode.log" 2>&1
done
python3 - <<'PY2'
import json
counts={}
for mode in ['old','fixed']:
 m=json.load(open(mode+'.json'))['modules']['keep_hc']
 ff=[c for c in m['cells'].values() if 'DFF' in c['type']]
 counts[mode]=sum(len(c['connections']['Q']) for c in ff)
assert counts['old']<41,counts
assert counts['fixed']==41,counts
print('HC_KEEP_SYNTH PASS',counts)
json.dump(dict(status='PASS',FF_counts=counts,expected_kept_bits=41),open('receipt.json','w'),indent=2)
PY2
