#!/bin/bash
# QW-DIEFIX ROMBIND (10-19 restart): GEN ROM bind audit with masks (+ empty-mask mutant) + XT1rb build/run (+ NOBIND mutant)
set -u
W=/srv/opentallas-scratch/claude/qw-diefix/xt1rb; S=$W/src; M=/srv/opentallas-scratch/claude/qw-diefix/masks_r0
DV=$W/die_dv2f16.v
cd $W
mkdir -p audit; cp $DV audit/die_dv2f16.v
python3 $W/tools/die_rom_bind.py audit/die_dv2f16.v --root $S --masks $M/manifest.json --rank 0 --out-dir audit/full > audit/audit_full.txt 2>&1; echo "rc=$?" >> audit/audit_full.txt
# mutant: one mask file emptied (symlink farm copy of the rank0 mask dir)
rm -rf mut_empty; mkdir -p mut_empty/rank0/masks
for f in $M/rank0/masks/*; do ln -s $f mut_empty/rank0/masks/; done
victim=$(ls mut_empty/rank0/masks | grep viamap | head -1); rm mut_empty/rank0/masks/$victim; : > mut_empty/rank0/masks/$victim
echo "emptied $victim" > audit/audit_mut_empty.txt
python3 $W/tools/die_rom_bind.py audit/die_dv2f16.v --root $S --masks mut_empty/rank0/manifest.json --rank 0 --out-dir audit/mut >> audit/audit_mut_empty.txt 2>&1; echo "rc=$?" >> audit/audit_mut_empty.txt
mkdir -p rb nobind; ln -sfn $W/prep rb/prep; ln -sfn $W/prep nobind/prep; ln -sfn $S rb/src; ln -sfn $S nobind/src
( XT1_TB=tb_xt1_rb.sv XT1_OBJ=obj bash $S/rtl/test/qwen_dv/xhead/run_xt1.sh $W/rb nominal:8:4 nominal:4:2 > rb.out 2>&1 )
( XT1_TB=tb_xt1_rb.sv XT1_OBJ=obj XT1_DEFS="+define+OT_XT1_NOBIND" bash $S/rtl/test/qwen_dv/xhead/run_xt1.sh $W/nobind nominal:8:4 > nobind.out 2>&1 )
echo XT1RB_DONE
