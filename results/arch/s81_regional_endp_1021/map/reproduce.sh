#!/bin/bash
set -euo pipefail
mkdir -p ../out
LIB=/srv/opentallas-scratch/claude/codex-s81-currentabi-native-prod-1021/out/map/lib
for mode in w r; do
cat > ../out/$mode.sv <<EOF
module top(input ck,rsi,input [7:0] i,input [31:0] bank,input [3:0] vld, output [31:0] bank_o,output [3:0] vld_o,output [7:0] o);
EOF
if [ "$mode" = w ]; then
 echo 'ot_pl_land_local_w #(.W(8),.D(4)) u(.ck(ck),.rsi(rsi),.i(i),.bank(bank_o),.vld(vld_o),.epo());' >> ../out/$mode.sv
else
 echo "ot_pl_land_local_r #(.W(8),.D(4),.K(2)) u(.ck(ck),.rsi(rsi),.bank(bank),.vld(vld),.epo(12'b0),.o(o));" >> ../out/$mode.sv
fi
echo 'endmodule' >> ../out/$mode.sv
{
echo 'read_verilog -sv -DSYNTHESIS ot_pl_land.sv'
echo "read_verilog -sv ../out/$mode.sv"
for lib in SEQ SIMPLE AO OA INVBUF; do echo "read_liberty -lib $LIB/$lib.lib"; done
echo 'hierarchy -check -top top; synth -top top -flatten -noshare'
echo "dfflibmap -liberty $LIB/SEQ.lib"
echo "abc -liberty $LIB/SIMPLE.lib -liberty $LIB/AO.lib -liberty $LIB/OA.lib -liberty $LIB/INVBUF.lib -liberty $LIB/SEQ.lib"
echo 'clean'
echo "tee -o ../out/$mode.stat.json stat -json -liberty $LIB/SEQ.lib -liberty $LIB/SIMPLE.lib -liberty $LIB/AO.lib -liberty $LIB/OA.lib -liberty $LIB/INVBUF.lib"
echo "write_verilog -noattr ../out/$mode.mapped.v"
} > ../out/$mode.ys
docker run --rm -v /srv/opentallas-scratch/claude/codex-s81-ml-e2-1021:/srv/opentallas-scratch/claude/codex-s81-ml-e2-1021 -v "$LIB:$LIB:ro" -w "$PWD" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -l ../out/$mode.log ../out/$mode.ys"
 done
sha256sum ot_pl_land.sv "$LIB"/*.lib > ../out/source_identity.sha256
