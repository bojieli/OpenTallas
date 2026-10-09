#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-protected-pair-r3
src=(ot_gpu_w6_secded_pkg.sv ot_hdc_hbm_model.sv ot_qfd_protected_phy_pair_pc.sv tb_qfd_protected_phy_pair.sv)
for ooo in 0 1 2;do
 iverilog -g2012 -s tb_qfd_protected_phy_pair -Ptb_qfd_protected_phy_pair.OOO=$ooo -o pos$ooo "${src[@]}" > compile_pos$ooo.log 2>&1 || exit 2
 vvp pos$ooo > positive$ooo.log 2>&1 || exit 3
done
iverilog -g2012 -s tb_qfd_protected_phy_pair -Ptb_qfd_protected_phy_pair.OOO=2 -Ptb_qfd_protected_phy_pair.LONGSTALL=1 -o longstall "${src[@]}" > compile_longstall.log 2>&1 || exit 4
vvp longstall > longstall.log 2>&1 || exit 5
for n in 1 2 3 4 5 6 7;do
 iverilog -g2012 -s tb_qfd_protected_phy_pair -Ptb_qfd_protected_phy_pair.MUT=$n -o mut$n "${src[@]}" > compile_mut$n.log 2>&1 || exit 6
 vvp mut$n > mut$n.log 2>&1
 ec=$?;echo "MUT$n exit=$ec" >> verdict.txt
 [ "$ec" = 1 ] || exit 7
done
for kind in off rollover;do
 arg=ENABLE=0;[ "$kind" = rollover ] && arg=ROLL=1
 iverilog -g2012 -s tb_qfd_protected_phy_pair -Ptb_qfd_protected_phy_pair.$arg -o $kind "${src[@]}" > compile_$kind.log 2>&1 || exit 8
 vvp $kind > $kind.log 2>&1 || exit 9
done
sha256sum "${src[@]}" > source_sha256.txt
echo PASS_ALL >> verdict.txt
