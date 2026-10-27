W=/srv/opentallas-scratch2/claude/wt/qc-su-kits-1026; U=/srv/opentallas-scratch2/claude/wt/qc-su-kits-1026/results/master_plan_r5/su_unequal/su_tree_uf.py; LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor; LEF=/srv/opentallas-scratch2/claude/wt/qc-su-kits-1026/physical/asap7_memory_macros_v2
cd /srv/opentallas-scratch2/claude/qc-su-kits-1026
for a in "vmr $LIB/vmr_f3y90.72.geo 4" "rp1 $LIB/rp1_f3.geo 6 --trunk 250" "prog $LIB/prog_f3.geo 3"; do set -- $a; n=$1; geo=$2; k=$3; shift 3
 prlimit --as=16000000000 python3 -u $W/results/qc_su_kits/r1/su_kit_gate.py $n $geo $k $LIB $U $LEF $n.gate.json "$@" > $n.gate.log 2>&1 &
done; wait
