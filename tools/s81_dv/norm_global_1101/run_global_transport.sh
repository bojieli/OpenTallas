#!/bin/bash
set -euo pipefail
cd source
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_global_publication --build-jobs 4 -O1 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0' --Mdir ../obj ot_rst_relay.sv ot_s81sl_rstop.sv ot_s81sl_rstopt_xo.sv tb_global_publication.sv >../build.log 2>&1
set +e
../obj/Vtb_global_publication +MODE=0 >../HEAD_current.log 2>&1;h=$?
../obj/Vtb_global_publication +MODE=1 >../FFN_current.log 2>&1;f=$?
../obj/Vtb_global_publication +MODE=0 +SERIAL >../HEAD_serial_transport.log 2>&1;hs=$?
../obj/Vtb_global_publication +MODE=1 +SERIAL >../FFN_serial_transport.log 2>&1;fs=$?
../obj/Vtb_global_publication +MODE=0 +SERIAL +MUT_PAYLOAD >../payload_mutant.log 2>&1;m=$?
printf 'HEAD_CURRENT_RC=%d\nFFN_CURRENT_RC=%d\nHEAD_SERIAL_RC=%d\nFFN_SERIAL_RC=%d\nPAYLOAD_RC=%d\n' "$h" "$f" "$hs" "$fs" "$m" >../status.txt
cat ../status.txt
grep GLOBAL_PUBLICATION_RESULT ../HEAD_current.log ../FFN_current.log ../HEAD_serial_transport.log ../FFN_serial_transport.log ../payload_mutant.log
if [ "$h" -eq 0 ]||[ "$f" -eq 0 ]||[ "$hs" -ne 0 ]||[ "$fs" -ne 0 ]||[ "$m" -eq 0 ];then exit 1;fi
