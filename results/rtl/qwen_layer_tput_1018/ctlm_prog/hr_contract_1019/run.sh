#!/bin/bash
# QW-DIEFIX: tt_ctlm prog bench with the hr pack (m0) + HR_ASBUILT mutant, Verilator 5.050
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
W=/srv/opentallas-scratch/claude/qw-diefix/hrprog; S=$W/src
verilator --version > $W/verilator.version
cd $S
for img in image image_dv2f14bi; do
  python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img results/rtl/qwen_layer_tput_1018/ctlm_prog/$img --decode 3 --work $W/w_$img > $W/m0_$img.txt 2>&1; echo "rc=$?" >> $W/m0_$img.txt
done
python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img results/rtl/qwen_layer_tput_1018/ctlm_prog/image --decode 3 --hra 1 --work $W/w_image > $W/hra1_image.txt 2>&1; echo "rc=$?" >> $W/hra1_image.txt
echo HRPROG_DONE
