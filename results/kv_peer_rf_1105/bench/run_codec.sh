#!/bin/bash
# DIE-KV-70/PEER: codec lockstep and pair benches. usage: run_codec.sh OUT (repo root as cwd). m_* rows must FAIL.
set -u; B=results/kv_peer_rf_1105/bench; O=${1:-/tmp/peerc}; mkdir -p $O
R3=results/kv_peer_rf_1105/rtl/qkd_hr_core_peer; S=rtl/qwen_sys
RKS=$S/host_integrated_20261014/qkd_host_peer_rank_codec.sv; COS="$S/mu_qwen_20261018/qkd_host_peer_coordinator_codec_mu.sv $S/host_integrated_20261014/qkd_host_peer_coordinator_codec.sv"
RK=$R3/qkd_host_peer_rank_codec_r3.sv; CO=$R3/qkd_host_peer_coordinator_codec_r3.sv
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
bld(){ n=$1; top=$2; shift 2; $VL --binary --timing -Wno-fatal -Wno-lint --top-module $top -O1 "$@" $B/tb_codec.sv --Mdir $O/$n -o t > $O/$n.log 2>&1 || { echo "BUILD FAIL $n"; grep -m5 %Error $O/$n.log | cut -c1-200; }; }
row(){ echo "$1: $(timeout 400 $O/$2/t $3 | grep -E '^(DONE|FAULT|PASS|FAIL|ERR)' | tail -3 | tr '\n' ' ' | cut -c1-260)"; }
mut(){ python3 -I - "$1" "$2" "$3" "$4" <<'PY'
import sys
i,o,a,b=sys.argv[1:5]; s=open(i).read(); assert s.count(a)==1,a; open(o,'w').write(s.replace(a,b))
PY
}
bld rk tb_rank_ls $RKS $RK; bld co tb_co_ls $COS $CO; bld pr tb_pair $RK $CO
mut $RK $O/rk_m1.sv "if(hdr_bad||op_bad)fault<=1;" "if(op_bad)fault<=1;"; bld rkm1 tb_rank_ls $RKS $O/rk_m1.sv
mut $CO $O/co_m1.sv "rx_bad_q<=rx_fire&rx_bad;" "rx_bad_q<=rx_fire&rx_bad&~op3;"; bld com1 tb_co_ls $COS $O/co_m1.sv
mut $RK $O/rk_m2.sv "if(status!=status_prev)status_dirty<=1;" "if(status!=status_prev)status_dirty<=0;"; bld prm1 tb_pair $O/rk_m2.sv $CO
mut $CO $O/co_m2.sv "if(allocation_change)allocation_dirty[i]<=1;" "if(allocation_change)allocation_dirty[i]<=0;"; bld prm2 tb_pair $RK $O/co_m2.sv
for s in 1 2; do row "rank lockstep seed $s" rk +SEED=$s; row "coord lockstep seed $s" co +SEED=$s; row "pair r3 seed $s" pr +SEED=$s; done
row "rank m_nohdr (must FAIL)" rkm1 +SEED=1; row "coord m_nostatuscheck (must FAIL)" com1 +SEED=1
row "pair m_stat (must FAIL)" prm1 +SEED=1; row "pair m_dirty (must FAIL)" prm2 +SEED=1
