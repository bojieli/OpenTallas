#!/bin/bash
S=/srv/opentallas-scratch2/claude/rtlc2/selt_repo; cd $S; export PATH=$HOME/.local/opentallas-tools/bin:$PATH SIM=verilator VL_JOBS=8
cp rtl/selt.sv rtl/selt_new.sv
for sd in 1 2; do python3 tools/s81/rtl_lockstep_eq.py --top dsfd_selt_c --file rtl/selt.sv --ref-rev HEAD --out $S/out$sd --clk ck --seed $sd --cycles 5000 x/*.sv > $S/res$sd.txt 2>&1; echo rc=$? >> $S/res$sd.txt; done
cp rtl/selt_mut.sv rtl/selt.sv
python3 tools/s81/rtl_lockstep_eq.py --top dsfd_selt_c --file rtl/selt.sv --ref-rev HEAD --out $S/outm --clk ck --seed 1 --cycles 5000 x/*.sv > $S/resm.txt 2>&1; echo rc=$? >> $S/resm.txt
cp rtl/selt_new.sv rtl/selt.sv
