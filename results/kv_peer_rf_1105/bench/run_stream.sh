#!/bin/bash
# DIE-KV-70/PEER: mux and link stream benches, source against r3. usage: run_stream.sh OUT (repo root as cwd). The m_* rows must FAIL.
set -u; B=results/kv_peer_rf_1105/bench; O=${1:-/tmp/peers}; mkdir -p $O
R3=results/kv_peer_rf_1105/rtl/qkd_hr_core_peer
REFM=rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_root_mux.sv; REFL=rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_link.sv
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
bld(){ n=$1; top=$2; shift 2; $VL --binary --timing -Wno-fatal -Wno-lint --top-module $top -O1 "$@" --Mdir $O/$n -o t > $O/$n.log 2>&1 || { echo "BUILD FAIL $n"; tail -5 $O/$n.log; }; }
row(){ echo "$1: $($O/$2/t $3 | grep -E '^(DONE|FAULT|PASS|FAIL|ERR)' | tail -3 | tr '\n' ' ' | cut -c1-220)"; }
mut(){ python3 -I - "$1" "$2" "$3" "$4" <<'PY'
import sys
i,o,a,b=sys.argv[1:5]; s=open(i).read(); assert s.count(a)==1,a; open(o,'w').write(s.replace(a,b))
PY
}
bld mref tb_mux $REFM $B/tb_mux.sv
bld mr3 tb_mux -DUSE_R3 $R3/qkd_host_peer_root_mux_r3.sv $B/tb_mux.sv
bld mmut tb_mux -DUSE_R3 -DQKD_HR_PE_PL2_MUTANT $R3/qkd_host_peer_root_mux_r3.sv $B/tb_mux.sv
mut $R3/qkd_host_peer_root_mux_r3.sv $O/mux_m2.sv "if(hit!=0)physical_tx_data<=pick;" "physical_tx_data<=pick;"
bld mm2 tb_mux -DUSE_R3 $O/mux_m2.sv $B/tb_mux.sv
for s in 1 2 3; do row "mux src  seed $s" mref +SEED=$s; row "mux r3   seed $s" mr3 +SEED=$s; done
for b in 1 2; do row "mux src  bad $b" mref +BAD=$b; row "mux r3   bad $b" mr3 +BAD=$b; done
row "mux m_data (must FAIL)" mmut +SEED=1; row "mux m_txload (must FAIL)" mm2 +SEED=1
L=$R3/qkd_host_peer_link_r3.sv
bld lref tb_link $REFL $B/tb_link.sv
bld lr3 tb_link -DUSE_R3 $L $B/tb_link.sv
bld lm1 tb_link -DUSE_R3 -GMUTP=1 $L $B/tb_link.sv
mut $L $O/l_m2.sv "wire p_load=pf!=0&&(!phd_v||peer_pop);" "wire p_load=pf!=0;"
bld lm2 tb_link -DUSE_R3 $O/l_m2.sv $B/tb_link.sv
mut $L $O/l_m3.sv "normal_tx_cr<=normal_pop;" "normal_tx_cr<=n_load;"
bld lm3 tb_link -DUSE_R3 $O/l_m3.sv $B/tb_link.sv
mut $L $O/l_m4.sv "if(rx_pk_q&&(rx_pk_bad_q||pn==3'd4))fault<=1;" "if(rx_pk_q&&pn==3'd4)fault<=1;"
bld lm4 tb_link -DUSE_R3 $O/l_m4.sv $B/tb_link.sv
mut $L $O/l_m5.sv "+5'(peer_pop)-5'(returns!=0);" "-5'(returns!=0);"
bld lm5 tb_link -DUSE_R3 $O/l_m5.sv $B/tb_link.sv
for s in 1 2 3; do row "link src seed $s" lref +SEED=$s; row "link r3  seed $s" lr3 +SEED=$s; done
for b in 1 2 3 4; do row "link src bad $b" lref +BAD=$b; row "link r3  bad $b" lr3 +BAD=$b; done
row "link m_peerword (must FAIL)" lm1 +SEED=1; row "link m_phd_overwrite (must FAIL)" lm2 +SEED=1
row "link m_txcredit_early (must FAIL)" lm3 +SEED=1; row "link m_nobadcheck (BAD=1, must FAIL)" lm4 +BAD=1; row "link m_peer_credit_lost (must FAIL)" lm5 +SEED=1
