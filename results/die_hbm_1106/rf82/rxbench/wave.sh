#!/bin/bash
# DIE-HBM-82-RF 11-06: lock-step bench (HBM-GAPS-8 run_bm3.sh, gold = ot_pdie_serdes__fs + declared shift) for the RX no-macro forms + mutants
cd /srv/opentallas-scratch2/claude/die-hbm-82-rf/rxbench
R="7:0:0:1:7:7:PASS:2 7:0:0:2:7:2:PASS:2"
P="prlimit --as=40000000000 nice"
TAG=sr  SPF=ot_s81_kp4_sp.sv VDEF=+define+OT_RXBM3_FLOPDLY RUNS="$R" J=4 $P bash run_bm3.sh $PWD/out 9000 > run_sr.log 2>&1 &
TAG=fc  SPF=ot_s81_kp4_sp.sv VDEF="+define+OT_RXBM3_SRAM_SPLIT +define+OT_RXBM3_FLOPC" RUNS="$R" J=4 $P bash run_bm3.sh $PWD/out 9000 > run_fc.log 2>&1 &
TAG=mutA SPF=ot_s81_kp4_sp_mutA.sv VDEF=+define+OT_RXBM3_FLOPDLY RUNS="7:0:0:1:7:7:FAIL:2" J=4 $P bash run_bm3.sh $PWD/out 9000 > run_mutA.log 2>&1 &
TAG=mutC SPF=ot_s81_kp4_sp_mutC.sv VDEF="+define+OT_RXBM3_SRAM_SPLIT +define+OT_RXBM3_FLOPC" RUNS="7:0:0:1:7:7:FAIL:2" J=4 $P bash run_bm3.sh $PWD/out 9000 > run_mutC.log 2>&1 &
wait; echo WAVEDONE >> run_sr.log
