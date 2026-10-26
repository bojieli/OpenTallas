S=/srv/opentallas-scratch2/claude/wt/qc-su-kits3-1026; LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor; LEF=$S/physical/asap7_memory_macros_v2; G=$S/results/qc_su_kits/r4/su_kit_gate.py; R2=$S/results/qc_su_kits/r2
cd /srv/opentallas-scratch2/claude/su-kit-gate-1026/kits3/r4
r(){ n=$1; shift; prlimit --as=16000000000 python3 -u $G $n "$@" > $n.log 2>&1; }
for u in ls; do U=$S/results/qc_su_kits/r3/su_tree_uf_pc.py; [ $u = ls ] && U=$S/results/qc_su_kits/r4/su_tree_uf_ls.py
for k in 6 7; do for st in pin L3; do
 r btab_${u}_k${k}_${st} $R2/btab_m0.geo $k $LIB $U $LEF btab_${u}_k${k}_${st}.gate.json --trunk 250 --chain $( [ $st = pin ] || echo --straight $st ) &
done; done; done
wait
