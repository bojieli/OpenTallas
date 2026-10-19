#!/bin/bash
# MU-DQ-TOK (10-19): XT1rb column-slice matvec vehicle on the Qwen compute MU RELEASE die dv2f18dh2 (QW-TOK rerun 10-19, src 0d4c9808f).
#   src/ = the dv2f18mu GEN src files (ot-epyc6 /srv/opentallas-scratch/claude/mu-die-qw/dv2f18mu/src) + this bench;
#   die_dv2f18dh2.v = its out/case/die.v; ROM binding ONLY from the GEN (die_rom_bind.py, full-die audit with masks + --only
#   c16_W5_1 include); masks/gold = QW-XHEAD prep (real TP8 rank-0 L0 code ROMs, QW-REALSTG fixtures).
#   Builds: mu1 (qfd_dv_slice2 MU_NU 1) and mu4 (MU_NU 4, the release build; user 0 must be identical), mutant nobind (mu4).
#   STAND-INS (labelled): hr/x stream driven at the slice pins (no tt_ctlm, no die relays), one near cluster of 48, rs_i idle.
set -u
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; export PATH=$(dirname $VERILATOR):$PATH
W=/srv/opentallas-scratch/claude/qw-tok/xt1dh2; S=$W/src; P=/srv/opentallas-scratch/claude/qw-xhead-xt1/prep
M=/srv/opentallas-scratch/claude/qw-diefix/masks_r0
cd $W
mkdir -p audit
python3 $S/tools/qwen_split/die_rom_bind.py die_dv2f18dh2.v --root $S --masks $M/manifest.json --rank 0 --hash-sample 64 \
   --out-dir audit/full > audit/audit_full.txt 2>&1; echo "rc=$?" >> audit/audit_full.txt
python3 $S/tools/qwen_split/die_rom_bind.py die_dv2f18dh2.v --root $S --only c16_W5_1 --prefix '' --out-dir audit/xt1 \
   > audit/audit_xt1.txt 2>&1; echo "rc=$?" >> audit/audit_xt1.txt
cp audit/xt1/rom_bind.vh $S/rtl/test/qwen_dv/xhead/rom_bind_xt1.vh || { echo "NO rom_bind.vh"; exit 2; }
for v in mu1 mu4 nobind; do mkdir -p $v; ln -sfn $P $v/prep; ln -sfn $S $v/src; done
( XT1_TB=tb_xt1_rb.sv XT1_OBJ=obj XT1_DEFS="-GMU_NU=1" bash $S/rtl/test/qwen_dv/xhead/run_xt1.sh $W/mu1 nominal:8:4 nominal:4:2 > mu1.out 2>&1 ) &
( XT1_TB=tb_xt1_rb.sv XT1_OBJ=obj XT1_DEFS="-GMU_NU=4" bash $S/rtl/test/qwen_dv/xhead/run_xt1.sh $W/mu4 nominal:8:4 nominal:4:2 > mu4.out 2>&1 ) &
( XT1_TB=tb_xt1_rb.sv XT1_OBJ=obj XT1_DEFS="-GMU_NU=4 +define+OT_XT1_NOBIND" bash $S/rtl/test/qwen_dv/xhead/run_xt1.sh $W/nobind nominal:8:4 > nobind.out 2>&1 ) &
wait
for v in mu1 mu4; do for t in l8_g4 l4_g2; do
  f=$W/$v/log_nominal_$t.txt; [ -f $f ] && grep -v -E ' (TGO|TX|TOUT|XT) ' $f > $W/$v/ctl_$t.txt; done; done
grep -h '^RESULT' mu1.out mu4.out nobind.out
echo XT1MU_DONE
