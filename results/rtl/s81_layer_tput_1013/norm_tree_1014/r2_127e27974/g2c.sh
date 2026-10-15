#!/bin/bash
# g2c: production layer run (tb_s81_die_layer NG 256 HCH 1 FP dpi, --coef-split --h-stream, PIPE HST HTX 2 PGAP 600), L0 / L2:
# baseline (NTREE 0) and the NORM tree (NTREE 1 NT_K 67, + mut_hc), same commit, same binary options
SRC=$1; OUT=$2; mkdir -p $OUT
cd $SRC
export CASES=/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl NG=256 HCH=1 FP=dpi LAYERS="L0 L2" STIMX="--coef-split --h-stream" J=16
[ -x $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator ] && export VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
XG="-GPIPE=1 -GHST=1 -GHTX=2 -GPGAP=600" bash rtl/dsrom_sys/s81_ctrl/test/run_die_layer.sh $SRC $OUT/base "nom" > $OUT/base.log 2>&1 &
XG="-GPIPE=1 -GHST=1 -GHTX=2 -GPGAP=600 -GNTREE=1 -GNT_K=67" bash rtl/dsrom_sys/s81_ctrl/test/run_die_layer.sh $SRC $OUT/ntree "nom mut_hc" > $OUT/ntree.log 2>&1 &
wait
cat $OUT/base/verdicts.log $OUT/ntree/verdicts.log
