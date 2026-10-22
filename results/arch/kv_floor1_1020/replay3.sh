#!/bin/bash
# KV-FLOOR1 replay 3: (a) FLOOR=1 on the d11r table with die_bound.v's two pvw_*__u_ctl masters substituted ctl_tb -> ctl_tbf
# .END_FLOOR(1) (SYNTHETIC master substitution: the compiler/die agreement path; same ports, the table is unchanged);
# (b) unittest test_kv_static_programme + test_kv_pvw_padding with the archive incl results/arch/qwen_split_1014.
C=$1; B=/srv/opentallas-scratch/claude; RUN=$B/qwen-kvsys/kvs14r-04b625135-gen9d11r; O=$B/kvfloor1-replay-$C
exec /home/ubuntu/bin/ot-run --mem 16 --threads 4 --dir $RUN -- bash -c "set -u; M=$B/git-mirror/OpenTallas.git; W=$B/kvfloor1-src-$C; \
git --git-dir=\$M archive $C results/arch/qwen_split_1014 | tar -x -C \$W; cd \$W; K=$RUN/case_kv; \
sed -E 's/ot_qwen_tp8_pv_wide_ctl_tb( *#\( *)(\.FIRST_INPUT_AGE)/ot_qwen_tp8_pv_wide_ctl_tbf\1.END_FLOOR(1),\2/' $RUN/port_bind_v2/die_bound.v > $O/die_bound_tbf.v; \
echo SUBST \$(grep -c 'ot_qwen_tp8_pv_wide_ctl_tbf' $O/die_bound_tbf.v); \
OT_KV_PVFIN_FLOOR=1 timeout 3000 python3 tools/qwen_kv_die/kv_static_params.py --model \$K/static_model.json --table $RUN/relay_stages_netlist.json.gz --fwd-lanes $RUN/fwd_lanes.json --die-v $O/die_bound_tbf.v --case-die-v \$K/die.v --boot-out $O/boot_ages_f1s.json --out $O/static_params_f1s.json > $O/sp_f1s.log 2>&1; echo \"FLOOR=1S rc=\$?\"; tail -c 1200 $O/sp_f1s.log; echo; \
cd tools/qwen_kv_die; for F in 0 1; do OT_KV_PVFIN_FLOOR=\$F timeout 3000 python3 -m unittest test_kv_static_programme test_kv_pvw_padding > $O/unittest_f\$F.log 2>&1; echo \"UNITTEST FLOOR=\$F rc=\$?\"; tail -4 $O/unittest_f\$F.log; done"
