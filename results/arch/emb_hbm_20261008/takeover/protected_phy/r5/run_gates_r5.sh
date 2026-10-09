#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-protected-phy-r5
src=(ot_gpu_w6_secded_pkg.sv ot_hdc_hbm_model.sv ot_qfd_protected_phy_pc.sv tb_qfd_protected_phy.sv)
iverilog -g2012 -s tb_qfd_protected_phy -o positive_latency "${src[@]}" > compile_latency.log 2>&1 || exit 2
vvp positive_latency > positive_latency.log 2>&1 || exit 3
for n in 1 2 3 4; do
  iverilog -g2012 -s tb_qfd_protected_phy -Ptb_qfd_protected_phy.MUT=$n -o mut$n "${src[@]}" > compile_mut$n.log 2>&1 || exit 4
  vvp mut$n > mut$n.log 2>&1
  ec=$?
  echo "MUT$n exit=$ec" >> verdict.txt
  [ "$ec" = 1 ] || exit 5
done
iverilog -g2012 -s tb_qfd_protected_phy -Ptb_qfd_protected_phy.ENABLE=0 -o off "${src[@]}" > compile_off.log 2>&1 || exit 6
vvp off > off.log 2>&1 || exit 7
sha256sum "${src[@]}" > source_sha256.txt
iverilog -g2012 -s tb_qfd_protected_phy -Ptb_qfd_protected_phy.ROLL=1 -o rollover "${src[@]}" > compile_rollover.log 2>&1 || exit 8
vvp rollover > rollover.log 2>&1 || exit 9
echo PASS_ALL >> verdict.txt
