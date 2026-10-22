#!/bin/bash
# KV-FLOOR1: kv_static_params replay at COMMIT on the UNCHANGED gen9d11r run (ep6), flag off (control) and OT_KV_PVFIN_FLOOR=1,
# plus the pytest files touched by the floor change. Unpinned ot-run; --dir = the d11r run (data locality).
C=$1; B=/srv/opentallas-scratch/claude; RUN=$B/qwen-kvsys/kvs14r-04b625135-gen9d11r; O=$B/kvfloor1-replay-$C
exec /home/ubuntu/bin/ot-run --mem 16 --threads 4 --dir $RUN -- bash -c "set -u; M=$B/git-mirror/OpenTallas.git; W=$B/kvfloor1-src-$C; \
git -C \$M fetch -q https://github.com/bojieli/OpenTallas claude/kv-floor1-1020; \
mkdir -p \$W; git --git-dir=\$M archive $C tools rtl results/arch/qwen_kv_static_programme_1017 results/arch/qwen_kv_die \
 results/rtl/qwen_layer_tput_1018 results/arch/qwen_split_compute_1014 physical/asap7_memory_macros_v2 | tar -x -C \$W; \
mkdir -p $O; cd \$W; K=$RUN/case_kv; A=\"--model \$K/static_model.json --table $RUN/relay_stages_netlist.json.gz --fwd-lanes $RUN/fwd_lanes.json --die-v $RUN/port_bind_v2/die_bound.v --case-die-v \$K/die.v\"; \
for F in 0 1; do OT_KV_PVFIN_FLOOR=\$F timeout 3000 python3 tools/qwen_kv_die/kv_static_params.py \$A --boot-out $O/boot_ages_f\$F.json --out $O/static_params_f\$F.json > $O/sp_f\$F.log 2>&1; echo \"FLOOR=\$F rc=\$?\"; tail -c 1500 $O/sp_f\$F.log; echo; done; \
cd tools/qwen_kv_die; for F in 0 1; do OT_KV_PVFIN_FLOOR=\$F timeout 3000 python3 -m unittest -q test_kv_static_programme test_kv_pvw_padding > $O/pytest_f\$F.log 2>&1; echo \"PYTEST FLOOR=\$F rc=\$?\"; tail -5 $O/pytest_f\$F.log; done"
