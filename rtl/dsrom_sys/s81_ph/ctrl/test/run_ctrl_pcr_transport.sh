#!/bin/bash
# S81-TRANSPORT-FIX gate of ot_s81ph_ctrl_pcr at bound transport. Run from the repo root: run_ctrl_pcr_transport.sh <out dir>
# Good build: every depth PASS and no PHY refusal.  Controls that must fail: S81CTRL_MUT_CREDIT (limit PQD + 1), +FK=1.
set -u
O=${1:?out dir}; mkdir -p "$O"; C=rtl/dsrom_sys/s81_ph/ctrl; L=rtl/dsrom_sys/s81_link
b(){ verilator --binary --timing -j 4 --top-module tb_krdy -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-LATCH -Wno-CASEINCOMPLETE -Wno-BLKSEQ $2 -Mdir "$O/$1" \
  -y $C -y $L -y rtl/dsrom_sys/s81_ph -y rtl/dsrom_sys/s81_dv/common $L/ot_s81_hbm_pcc.sv $C/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv \
  $C/ot_s81ph_ctrl_pcr.sv $C/test/tb_ctrl_pcr_transport.sv >"$O/build_$1.log" 2>&1 || { echo BUILD FAIL $1; exit 2; }; }
b good ""; b mut "+define+S81CTRL_MUT_CREDIT"
rc=0
for d in "0 0" "1 0" "2 2" "5 4" "10 9" "15 12" "31 31"; do set -- $d
  for t in "+MAXL=1" "+MAXL=4" "+MAXL=4 +WP=50"; do
    "$O/good/Vtb_krdy" +DN=$1 +UP=$2 +MODE=0 +N=3000 +SEED=1 $t | grep RESULT | tee -a "$O/good.out" | grep -q ' PASS$' || { echo "FAIL good DN $1 UP $2 $t"; rc=1; }
    "$O/mut/Vtb_krdy" +DN=$1 +UP=$2 +MODE=0 +N=3000 +SEED=1 $t | grep RESULT | tee -a "$O/mut.out" | grep -q ' FAIL$' || { echo "MUTANT NOT CAUGHT DN $1 UP $2 $t"; rc=1; }
  done
done
"$O/good/Vtb_krdy" +DN=2 +UP=2 +MODE=0 +MAXL=4 +N=300 +SEED=1 +FK=1 | grep RESULT | grep -q 'fault 1 ' || { echo "k_bad CONTROL NOT CAUGHT"; rc=1; }
[ $rc = 0 ] && echo CTRL_PCR_TRANSPORT PASS || echo CTRL_PCR_TRANSPORT FAIL
exit $rc
