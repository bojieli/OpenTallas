#!/bin/bash
# NATIVE_BANKS VM equivalence: die_static (MEM=1) and tb_vmwb (5 PCs) at NATIVE_BANKS 0/1 + mutants
cd /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/src
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
( bash tools/qwen_tp8/vm_die_static_bench.sh /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n0 -GMEM=1 -GNATIVE_BANKS=0 > /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n0.out 2>&1; echo rc=$? >> /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n0.out ) &
( bash tools/qwen_tp8/vm_die_static_bench.sh /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n1 -GMEM=1 -GNATIVE_BANKS=1 > /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n1.out 2>&1; echo rc=$? >> /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n1.out ) &
( bash tools/qwen_tp8/vm_die_static_bench.sh /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n1_obs -GMEM=1 -GNATIVE_BANKS=1 -GOBS_MUT=1 > /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n1_obs.out 2>&1; echo rc=$? >> /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/ds_n1_obs.out ) &
for c in n0:-GNATIVE_BANKS=0 n1:-GNATIVE_BANKS=1 n1vp:-GNATIVE_BANKS=1,-GVPMUT=1; do n=${c%%:*}; a=$(echo ${c#*:} | tr , ' ');
 ( J=12 bash tools/qwen_vmwb/build_bench.sh /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/wb_$n -GVARIANT=1 -GTE=13 $a && while read -r pc args; do echo "$n $pc $(/srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/wb_$n/obj/Vtb_vmwb $args 2>&1 | grep -E '^\{|^PASS|^FAIL vmwb' | tr '\n' ' ')"; done < results/arch/qwen_split_compute_1014/vmwb_1015/pcs.txt > /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/wb_$n.results ) &
done
wait; echo ALLDONE > /srv/opentallas-scratch/claude/q-vmwb/nb-48155cb29/done
