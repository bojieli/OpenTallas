#!/bin/bash
# run_boot_secded.sh <src root> <out dir>: (c) RoPE boot + (d) SECDED bench. Lines: base m0 (PASS), +badsum, +short
# (PASS = rejected), MUT 1 and MUT 2 (must FAIL).  Image from tools/s81_ctrl/rope_boot_image.py (top 64 positions).
set -u
SRC=$1; OUT=$2; mkdir -p $OUT; S=$SRC/rtl/dsrom_sys/s81_ctrl
python3 $SRC/tools/s81_ctrl/rope_boot_image.py --max-pos 64 --top --out $OUT/img > $OUT/img.log 2>&1 || { echo IMG_FAIL; cat $OUT/img.log; exit 1; }
for m in 0 1 2; do
  verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_boot_secded -GMUT=$m --Mdir $OUT/b$m -o tb \
    $S/ot_s81_boot_seq.sv $S/ot_s81_secded.sv $S/test/tb_s81_boot_secded.sv > $OUT/b$m.log 2>&1 || { echo BUILD_FAIL $m; grep -m5 -i error $OUT/b$m.log; exit 1; }
done
A="+img=$OUT/img/rope.hex +meta=$OUT/img/rope_meta.txt"
L=$OUT/boot_secded.log; : > $L
echo "# base" >> $L; timeout 900 $OUT/b0/tb $A 2>&1 | grep TB_S81 >> $L
echo "# badsum" >> $L; timeout 900 $OUT/b0/tb $A +badsum 2>&1 | grep TB_S81 >> $L
echo "# short" >> $L; timeout 900 $OUT/b0/tb $A +short 2>&1 | grep TB_S81 >> $L
echo "# MUT1 decoder never corrects (expect FAIL)" >> $L; timeout 900 $OUT/b1/tb $A 2>&1 | grep TB_S81 >> $L
echo "# MUT2 encoder drops overall parity (expect FAIL)" >> $L; timeout 900 $OUT/b2/tb $A 2>&1 | grep TB_S81 >> $L
cat $L
