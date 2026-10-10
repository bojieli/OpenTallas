#!/bin/bash
set -eu
O=$1; M=${2:-0}; mkdir -p "$O"
R=$(cd "$(dirname "$0")/../../.." && pwd); cd "$R"
cp physical/hbm_generic/token18/facade_fixture/hfd_mtp_generic18.sv "$O/facade.sv"
if [ "$M" = 1 ];then sed -i 's/\.p_tok(f_cmdproc\[38 +: 18\])/\.p_tok({1\x27b0,f_cmdproc[38 +: 17]})/' "$O/facade.sv";fi
if [ "$M" = 2 ];then sed -i 's/wire rst_n=~rst_s\[1\];/wire rst_n=~rst[0];/' "$O/facade.sv";fi
source physical/qwen_die_masters/cfg/hgi_mtp_core18.env
iverilog -g2012 -s tb_hgi_mtp_die_facade -o "$O/sim" $SRCS "$O/facade.sv" physical/hbm_generic/token18/tb_hgi_mtp_die_facade.sv > "$O/build.log" 2>&1 || { cat "$O/build.log";exit 2; }
set +e
vvp -n "$O/sim" > "$O/run.log" 2>&1
rc=$?;cat "$O/run.log";exit "$rc"
