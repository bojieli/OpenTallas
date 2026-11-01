#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cat > native.sv <<'SV'
module native(input ck,rst_n,input[7:0]d,input en,output deferred,output fault);
reg[2:0]a;reg[4:0]b;reg f,g;
always @(posedge ck or negedge rst_n) if(!rst_n)begin a<=0;b<=0;f<=1;g<=0;end else begin if(en)begin a<=d[2:0];b<=d[7:3];end f<=f^d[0];g<=g|d[1];end
assign deferred=(|a)||(|b);assign fault=f|g;
endmodule
SV
yosys -Q -T -p 'read_verilog native.sv; hierarchy -top native; proc; flatten; opt_clean; write_json native.json' > native.log 2>&1
python3 hr_state_outputs.py stage native.json cone.json manifest.json --top native --output deferred --output fault > stage.log
yosys -Q -T -p 'read_json cone.json; opt_expr; opt_clean; write_json folded.json' > fold.log 2>&1
python3 hr_state_outputs.py finish folded.json gate.json manifest.json > finish.log
python3 hr_state_outputs.py finish folded.json mutant.json manifest.json --mutant > finish_mut.log
for v in gate mutant; do
 cat > "$v.ys" <<EOF
read_json native.json
rename native gold
read_json $v.json
rename native gate
async2sync
opt_clean
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
EOF
 set +e; yosys -Q -T "$v.ys" > "$v.log" 2>&1; rc=$?;set -e
 echo "$rc" > "rc_$v"
done
test "$(cat rc_gate)" = 0
test "$(cat rc_mutant)" = 1
printf 'TINY_STATE_RECUT PASS0/MUT1 (mixed0/1reset, gateddata,2ORoutputs)\n'
