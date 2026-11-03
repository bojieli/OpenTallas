#!/bin/bash
# TOK-QW-5 A/B: one compute block (cbx_q10__cl94a12200, tiles 708..711): ROM arrays after load, A = ROM_TILE defparams + +OT_ROM_DIR (the build0 bench law), B = hierarchical readmemh + +OT_TB_ROM_DIR; both with hier_block matvec_part.
set -uo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
V=$1; R=/srv/opentallas-scratch2/claude/tok-qk-2; D=/srv/opentallas-scratch2/claude/tok-qw-5/abtest; cd $R/stage1
/usr/bin/time -v -o $D/build_$V.time verilator --binary --hierarchical -j 8 -O0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 -CFLAGS "-O1 -w" --Mdir $D/obj_$V -o Vtb_ab \
  $(cat defines.f) +define+OT_S6_SIM $(cat incdirs.f) +incdir+$D +incdir+../veh0 +incdir+../qc59q --top-module tb_ab /srv/opentallas-scratch2/claude/tok-qw-5/build1/hier.vlt \
  $(grep -v "qfd_sys_face_lctx3_core.sv\|qfd_dv_head_safe1.sv" files.f) ../qc59q/qfd_sys_face_lctx3_core.sv ../qc59q/qfd_sysface_cseq_single.sv ../qc59q/qfd_dv_head_safe1.sv $D/tb_$V.sv > $D/build_$V.log 2>&1
echo "BUILD_RC_$V=$? $(grep -o "Maximum resident set size (kbytes): [0-9]*" $D/build_$V.time) $(grep -o "Elapsed.*" $D/build_$V.time)" >> $D/status
mkdir -p $D/dump_$V
if [ $V = A ]; then P=+OT_ROM_DIR=$R/roms_qc_r0; else P=+OT_TB_ROM_DIR=$R/roms_qc_r0; fi
$D/obj_$V/Vtb_ab $P +OD=$D/dump_$V > $D/sim_$V.log 2>&1; echo "SIM_RC_$V=$?" >> $D/status
