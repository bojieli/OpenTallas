#!/bin/bash
# cp2 (H-NETLIST 2026-10-15) benches: static cfg collar + status join + real ingress; static host packet; host PHY adapter.
# Every mutant must FAIL.   bash rtl/hbm_accel/host_static_20261015/run_cp2.sh [OUT_DIR]
set -u
cd "$(dirname "$0")/../../.."
D=rtl/hbm_accel/host_static_20261015; O=${1:-/tmp/cp2-bench}; mkdir -p $O; rc=0
run(){ # name expect(PASS|FAIL) files... -- defines
  local n=$1 want=$2; shift 2; iverilog -g2012 "$@" -o $O/$n.vvp >$O/$n.build 2>&1 || { echo "BUILD-ERR $n"; rc=1; return; }
  local r; r=$(vvp -n $O/$n.vvp | grep -E '^(PASS|FAIL)' | tail -1); echo "$n: $r"
  case "$r" in $want*) ;; *) echo "UNEXPECTED $n (wanted $want)"; rc=1;; esac; }
C="$D/tb_hbm_static_cfg_collar.sv $D/ot_hbm_static_cfg_collar.sv $D/ot_hbm_status_join.sv $D/ot_hbm_host_static_ingress.sv"
run collar PASS $C
for m in 1 2 3 4; do run collar_mut$m FAIL -Ptb_hbm_static_cfg_collar.CMUT=$m $C; done
for m in 1 2; do run join_mut$m FAIL -Ptb_hbm_static_cfg_collar.JMUT=$m $C; done
P="$D/tb_hbm_host_packet_static.sv $D/ot_hbm_host_packet_static.sv $D/ot_hbm_host_static_ingress.sv"
run packet PASS $P
for m in 1 2 3; do run packet_mut$m FAIL -Ptb_hbm_host_packet_static.MUT=$m $P; done
A="$D/tb_hbm_host_phy_adapt.sv $D/ot_hbm_host_phy_adapt.sv"
run phy PASS $A
for m in 1 2; do run phy_mut$m FAIL -Ptb_hbm_host_phy_adapt.MUT=$m $A; done
[ $rc = 0 ] && echo "CP2 BENCHES PASS (3 positive, 12 mutants rejected)" || echo "CP2 BENCHES FAIL"
exit $rc
