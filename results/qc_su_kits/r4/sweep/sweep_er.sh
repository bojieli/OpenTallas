S=/srv/opentallas-scratch2/claude/wt/qc-su-kits3-1026; LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor; LEF=$S/physical/asap7_memory_macros_v2; G=$S/results/qc_su_kits/r3/su_kit_gate.py; R2=$S/results/qc_su_kits/r2; U=$S/results/qc_su_kits/r4/su_tree_uf_er.py
cd /srv/opentallas-scratch2/claude/su-kit-gate-1026/kits3
r(){ n=$1; shift; prlimit --as=16000000000 python3 -u $G $n "$@" > $n.log 2>&1; }
for k in 4 5 6 7 8; do for st in pin L3 L2,L3; do
 r btab_er_k${k}_${st/,/} $R2/btab_m0.geo $k $LIB $U $LEF btab_er_k${k}_${st/,/}.gate.json --trunk 250 $( [ $st = pin ] || echo --straight $st ) &
done; done
wait
