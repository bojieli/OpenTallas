#!/bin/bash
# MU-DQ-DHUSER: Verilator (the closure daemon's 5.050) bench of qfd_sys_face_mu_dhobs.  $1 = source root; out in $2.
# Files read: rtl/qwen_split/mu/qfd_sys_face_mu_dhobs.sv, rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv,
#             physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v (elaborated only at OPSEG 1: not here),
#             results/rtl/mu_qwen_1018/dhobs/tb_dhobs.sv
set -u
S=$1; O=$2; V=${VERILATOR:-verilator}
mkdir -p $O; $V --version > $O/verilator_version.txt
$V --binary --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED --top-module tb_dhobs -Mdir $O/obj \
  $S/rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv $S/rtl/qwen_split/mu/qfd_sys_face_mu_dhobs.sv \
  $S/results/rtl/mu_qwen_1018/dhobs/tb_dhobs.sv > $O/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $O/build.log; exit 2; }
$O/obj/Vtb_dhobs > $O/pass.out 2>&1; tail -1 $O/pass.out
$O/obj/Vtb_dhobs +bad=50 > $O/bad50.out 2>&1; tail -1 $O/bad50.out
$O/obj/Vtb_dhobs +bad=1000 > $O/bad1000.out 2>&1; tail -1 $O/bad1000.out
