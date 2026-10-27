S=/srv/opentallas-scratch2/claude/wt/su-kit-gate-1026; LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor; LEF=$S/physical/asap7_memory_macros_v2; G=$S/results/qc_su_kits/r3/su_kit_gate.py; R2=$S/results/qc_su_kits/r2; U2=$S/results/qc_su_kits/r3/su_tree_uf_pc.py
cd /srv/opentallas-scratch2/claude/su-kit-gate-1026
r(){ n=$1; shift; prlimit --as=16000000000 python3 -u $G $n "$@" > $n.log 2>&1; }
for d in prog btab; do for k in 4 5 6; do for st in pin L3 L2,L3; do
 r ${d}_m0_k${k}_${st/,/} $R2/${d}_m0.geo $k $LIB $U2 $LEF ${d}_m0_k${k}_${st/,/}.gate.json --trunk 250 $( [ $st = pin ] || echo --straight $st ) &
done; done; done
wait
