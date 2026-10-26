S=/srv/opentallas-scratch2/claude/wt/su-kit-gate-1026; LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor; LEF=$S/physical/asap7_memory_macros_v2; G=$S/results/qc_su_kits/r3/su_kit_gate.py; R2=$S/results/qc_su_kits/r2; U2=$S/results/qc_su_kits/r3/su_tree_uf_pc.py
cd /srv/opentallas-scratch2/claude/su-kit-gate-1026
r(){ n=$1; shift; prlimit --as=16000000000 python3 -u $G $n "$@" > $n.log 2>&1; }
r prog_m0_r3 $R2/prog_m0.geo 6 $LIB $U2 $LEF prog_m0_r3.gate.json --trunk 250 --straight L3 &
r btab_m0_r3 $R2/btab_m0.geo 6 $LIB $U2 $LEF btab_m0_r3.gate.json --trunk 250 --straight L3 &
r prog_m0_k6_legacy $R2/prog_m0.geo 6 $LIB $S/results/qc_su_kits/r3/su_tree_uf_r5.py $LEF prog_m0_k6_legacy.gate.json --legacy-paths &
wait
