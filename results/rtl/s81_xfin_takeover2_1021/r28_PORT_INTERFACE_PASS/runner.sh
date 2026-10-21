#!/bin/bash
set -euo pipefail
R=$(pwd);mkdir -p port_fast_r4/obj
cat > port_fast_r4/map.ys <<'YS'
read_verilog -sv /work/port_fast_r4/mask_map.sv
hierarchy -check -top mask_map
synth -top mask_map
abc -liberty /work/out_mul_native/ao.lib -liberty /work/out_mul_native/invbuf.lib -liberty /work/out_mul_native/oa.lib -liberty /work/out_mul_native/simple.lib
write_verilog -noattr /work/port_fast_r4/mapped.v
YS
docker run --rm -v "$R:/work" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -s /work/port_fast_r4/map.ys' > port_fast_r4/synth.log 2>&1
printf 'read_verilog /work/port_fast_r4/mapped.v
puts "CURRENT_MAPPED_PARSER_PASS"
exit
' > port_fast_r4/parser.tcl
docker run --rm -v "$R:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /work/port_fast_r4/parser.tcl > port_fast_r4/parser_current.log 2>&1
cat port_fast_r4/parser_current.log
grep -q CURRENT_MAPPED_PARSER_PASS port_fast_r4/parser_current.log
printf 'read_verilog /work/eng_readonly/mapped.v
puts "OLD_PARSER_UNEXPECTED_PASS"
exit
' > port_fast_r4/parser_old.tcl
docker run --rm -v "$R:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /work/port_fast_r4/parser_old.tcl > port_fast_r4/parser_old.log 2>&1 || true
grep -q STA-0171 port_fast_r4/parser_old.log
if grep -q OLD_PARSER_UNEXPECTED_PASS port_fast_r4/parser_old.log; then echo OLD_PARSER_UNEXPECTED_PASS;exit 1;fi
echo OLD_SIGNED_PORT_PARSER_FAILED_AS_EXPECTED
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -O1 -Wno-fatal -Wno-WIDTH --top-module mask_tb -Mdir "$R/port_fast_r4/obj" "$R/port_fast_r4/mask_tb.sv" > port_fast_r4/build.log 2>&1
"$R/port_fast_r4/obj/Vmask_tb" > port_fast_r4/run.log 2>&1
cat port_fast_r4/run.log
grep -q 'comparisons=24576 bad=0' port_fast_r4/run.log
