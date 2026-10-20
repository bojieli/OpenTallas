#!/bin/bash
# QW-DIEFIX redstn2 last-k: dv_bench2 k + regression a..j (MUT 0), k under MUT 14 (kcm1 ignored); Verilator 5.050
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
R=/srv/opentallas-scratch/claude/qw-diefix/redstn2; S=$R/src
verilator --version > $R/verilator.version
cd $S
python3 -u rtl/test/qwen_dv/dv_bench2.py k --mut 14 --work $R/w > $R/m14.txt 2>&1; echo "rc=$?" >> $R/m14.txt
for b in k a b c d e f g h i j; do python3 -u rtl/test/qwen_dv/dv_bench2.py $b --mut 0 --work $R/w >> $R/m0.txt 2>&1; echo "rc=$? ($b)" >> $R/m0.txt; done
echo REDSTN2_DONE
