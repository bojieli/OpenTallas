#!/bin/bash
# TOK-QW-5 build1: whole-QC vehicle (TOK-QK-2 build0 inputs unchanged) with (1) hier_block ot_qwen_w12_matvec_part
# (88% of every compute-block flattened netlist, 768 instances) and (2) tb ROM loads by hierarchical readmemh
# instead of 768 tile ROM_TILE defparams (no per-tile specialisation). Flat build0 was MEMCG-OOM at 360 GiB.
set -uo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
R=/home/ubuntu/scratch-root/claude/tok-qw-5/qk2; B=/home/ubuntu/scratch-root/claude/tok-qw-5/build1; cd $R/stage1
echo "START $(date -Is)" > $B/status
/usr/bin/time -v -o $B/verilate.time verilator --binary --hierarchical -j ${OT_J:-16} --build-jobs ${OT_BJ:-8} -O0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --x-assign 0 --x-initial 0 --output-split 20000 --output-groups 256 -CFLAGS "-O1 -w" --Mdir $B/obj -o Vtb_qcdie \
  $(cat defines.f) +define+OT_S6_SIM $(cat incdirs.f) +incdir+$B +incdir+../veh0 +incdir+../qc59q --top-module tb_qcdie $B/hier.vlt \
  $(grep -v "qfd_sys_face_lctx3_core.sv\|qfd_dv_head_safe1.sv" files.f) ../qc59q/qfd_sys_face_lctx3_core.sv ../qc59q/qfd_sysface_cseq_single.sv ../qc59q/qfd_dv_head_safe1.sv ../veh0/qc_prog_rom_guard.sv ../veh0/start_stages_fn.sv $B/tb_qcdie.sv \
  > $B/build.log 2>&1
rc=$?; echo "BUILD_RC=$rc $(date -Is) $(grep -o "Maximum resident set size (kbytes): [0-9]*" $B/verilate.time) $(grep -o "Elapsed.*" $B/verilate.time)" >> $B/status
[ $rc = 0 ] && [ -x $B/obj/Vtb_qcdie ] || exit $rc
/usr/bin/time -v -o $B/sim.time $B/obj/Vtb_qcdie +OT_TB_ROM_DIR=$R/roms_qc_r0 +NCYC=${NCYC:-6000} > $B/sim.log 2>&1
rc=$?; echo "SIM_RC=$rc $(date -Is) $(grep -o "Maximum resident set size (kbytes): [0-9]*" $B/sim.time) $(grep -o "Elapsed.*" $B/sim.time)" >> $B/status
exit $rc
