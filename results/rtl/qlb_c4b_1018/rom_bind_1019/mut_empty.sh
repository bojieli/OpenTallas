#!/bin/bash
W=/srv/opentallas-scratch/claude/qw-diefix/xt1rb; M=/srv/opentallas-scratch/claude/qw-diefix/masks_r0; cd $W
cp $M/rank0/manifest.json mut_empty/rank0/
echo "emptied $(ls -l mut_empty/rank0/masks | grep -v -- '->' | grep viamap | awk '{print $NF, $5}')" > audit/audit_mut_empty.txt
python3 $W/tools/die_rom_bind.py audit/die_dv2f16.v --root $W/src --masks mut_empty/rank0/manifest.json --rank 0 --out-dir audit/mut >> audit/audit_mut_empty.txt 2>&1; echo "rc=$?" >> audit/audit_mut_empty.txt
cat audit/audit_mut_empty.txt
