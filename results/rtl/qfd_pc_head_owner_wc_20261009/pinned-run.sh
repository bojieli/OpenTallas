#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/ds-control/pc-head-owner-wc-937531860
sha256sum rtl/qwen_sys/system_20261009/ot_qfd_pc_head_owner_cl.sv rtl/common/ot_secded.sv rtl/common/ot_secded_cols.svh rtl/test/qwen_system/tb_qfd_pc_head_owner.sv pinned-run.sh > source.sha256
iverilog -V > tool-version.log 2>&1
S=(rtl/qwen_sys/system_20261009/ot_qfd_pc_head_owner_cl.sv rtl/common/ot_secded.sv rtl/test/qwen_system/tb_qfd_pc_head_owner.sv)
/usr/bin/time -v iverilog -g2012 -DPCO_CL -Irtl/common -s tb_qfd_pc_head_owner -o exact.vvp "${S[@]}" > exact.build.log 2>&1
/usr/bin/time -v vvp exact.vvp > exact.log 2>&1
grep -q 'PASS pcowner finite16' exact.log
grep -q 'PASS pcowner all432stored singlebit corrections' exact.log
grep -q 'PASS pcowner UE overflow wrongID duplicatehalf' exact.log
/usr/bin/time -v iverilog -g2012 -DPCO_CL -Ptb_qfd_pc_head_owner.MUT=1 -Irtl/common -s tb_qfd_pc_head_owner -o mutant.vvp "${S[@]}" > mutant.build.log 2>&1
set +e
/usr/bin/time -v vvp mutant.vvp > mutant.log 2>&1
mut_rc=$?
set -e
if [[ $mut_rc == 0 ]];then echo UNEXPECTED_MUTANT_PASS;exit 1;fi
grep -q 'NEG_DETECTED pcowner incorrect SECDED encoder' mutant.log
printf 'PC_HEAD_OWNER_CL W-c fixed937531860 exactPASS finite16 CE432 UE overflow wrongID duplicatehalf; genuineMUT_ECC1 expectedFAIL rc%s\n' "$mut_rc" > terminal.log
