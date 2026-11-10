#!/bin/bash
# HBM-CORES-B q3bc CF2 lockstep: clean gate, then one runtime-mutant gate (+mut=1..5). Two builds, cap 64G (48G OOMed in the front-end).
cd /srv/opentallas-scratch2/claude/hbm-cores-b/q3bc_sf
V=$HOME/.local/opentallas-tools/bin/verilator; K=../kits/q3bc_CF1b/rtl/ot_hfd_coll_q3_body_ctl.sv
python3 -I gen_cf2_tb.py || exit 1
for M in "" M4 MUX; do
 N=${M:-CF2}; python3 -I patch_cf2.py $K cf2/r_$N.sv $M | tail -n 1 | cut -c1-80
 awk '/^module ot_hfd_coll_q3_body_ctl_x\(/{p=1} p{print} p&&/^endmodule/{exit}' cf2/r_$N.sv | sed -E 's/^module ot_hfd_coll_q3_body_ctl_x\(/module ot_hfd_coll_q3_body_ctl_g(/' > cf2/gate_$N.sv; rm -f cf2/r_$N.sv
done
for N in CF2 MUX; do
 rm -rf cf2/obj_$N
 systemd-run --user --scope -q -p MemoryMax=64G $V --binary -j 8 --output-split 30000 --output-split-cfuncs 3000 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --x-initial 0 --x-assign 0 \
  -DSYNTHESIS -DOT_Q3CTL_TGTQ1 -DOT_Q3CTL_PREACC -DOT_Q3CTL_OFF4_RT -DOT_Q3CTL_CFG_CASE -DNTEST=30 -DRUN=800 --top-module tb -Mdir cf2/obj_$N -o sim tb_cf2.sv rtl/ot_hfd_coll_q3_body_ctl.sv cf2/gate_$N.sv rtl/ot_bodyctl_off32_split_d.sv rtl/ot_bodyctl_cfg_case.sv sram/*.v > cf2/build_$N.log 2>&1 || { echo "BUILD $N FAIL"; tail -n 5 cf2/build_$N.log | cut -c1-200; continue; }
 if [ $N = CF2 ]; then
  for G in 256 257 258 259 260 261 262 264; do echo "CF2 lgap $G: $(cf2/obj_CF2/sim +seed=1 +lgap=$G | grep LOCKSTEP | cut -c1-110)"; done
  for Sd in 2 3; do echo "CF2 s$Sd:"; cf2/obj_CF2/sim +seed=$Sd +lgap=264 | grep -E "LOCKSTEP|MISMATCH|RESTART_COVER|ASSERT" | head -n 4 | cut -c1-120; done
  echo "CF2 sweep:"; cf2/obj_CF2/sim +seed=1 +sweep=254 | grep SWEEP | sort -u -k3n | cut -c1-80
 else
  for Mu in 0 1 2 3 4 5; do echo "MUT $Mu:"; cf2/obj_MUX/sim +seed=2 +lgap=264 +mut=$Mu | grep -E "LOCKSTEP|MISMATCH|RESTART_COVER|ASSERT" | head -n 3 | cut -c1-120; done
  echo "MUT 4 sweep:"; cf2/obj_MUX/sim +seed=1 +sweep=254 +mut=4 | grep SWEEP | sort -u -k3n | cut -c1-80
 fi
done
echo DONE
