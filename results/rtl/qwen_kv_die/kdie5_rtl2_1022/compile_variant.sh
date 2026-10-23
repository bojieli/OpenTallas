#!/bin/bash
# cd.sh TAG "EXTRA ENV" : kv_static_programme die compile (--no-mu) on the relm ages with the release flags + EXTRA
T=$1; X="$2"; I=/home/ubuntu/ot-scratch/claude/kdie5-rtl/lc_in; W=/home/ubuntu/wt/kdie5-rtl2-1022
O=/home/ubuntu/ot-scratch/claude/kdie5-rtl2; cd $W; set -a; source $I/kv_flags.env; for kv in $X; do export $kv; done; export OT_KV_RETIRE_SUCCESSOR=$I/health_successor.json; export OT_KV_RETIRE_LOGICAL=1; set +a
env | grep -E 'OT_KV_(GRP_R2|CTL_|POR)' | sort > $O/cd_$T.env
python3 tools/qwen_kv_die/kv_grp_r2_compile_delta.py --ages $I/die_ages_fwd.json --out $O/cd_$T.json --no-mu --write $O/kpw_$T > $O/cd_$T.log 2>&1
echo "rc=$?" >> $O/cd_$T.log
