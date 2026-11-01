#!/bin/bash
set -euo pipefail
cd source
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_global_publication --build-jobs 4 -O1 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --output-split 5000 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0' --Mdir ../obj ot_rst_relay.sv ot_s81sl_rstop.sv ot_s81sl_rstopt_xo.sv tb_global_publication.sv >../build.log 2>&1
set +e
../obj/Vtb_global_publication +MODE=0 >../HEAD.log 2>&1;h=$?
../obj/Vtb_global_publication +MODE=1 >../FFN.log 2>&1;f=$?
../obj/Vtb_global_publication +MODE=0 +MUT_HOLD >../wrong_hold.log 2>&1;m=$?
printf 'HEAD_RC=%d\nFFN_RC=%d\nWRONG_HOLD_RC=%d\n' "$h" "$f" "$m" >../status.txt
cat ../status.txt
grep -E 'GLOBAL_QREL_DATE_ERRORS|GLOBAL_PUBLICATION_RESULT' ../HEAD.log ../FFN.log ../wrong_hold.log
if [ "$h" -ne 0 ]||[ "$f" -ne 0 ]||[ "$m" -eq 0 ];then exit 1;fi
