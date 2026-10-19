#!/bin/bash
# MU-DQ-DHUSER: Verilator (the closure daemon's 5.050) bench of qfd_sys_face_mu_dhobs.  Run from the source root:
#   [MUT=2] bash results/rtl/mu_qwen_1018/dhobs/run_dhobs.sh OUT [+bad=N]      (prints the TB_DHOBS verdict line)
# Files read: rtl/qwen_split/mu/qfd_sys_face_mu_dhobs.sv, rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv,
#             results/rtl/mu_qwen_1018/dhobs/tb_dhobs.sv
set -u
O=$1; shift; V=${VERILATOR:-verilator}
mkdir -p $O; $V --version > $O/verilator_version.txt
$V --binary --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED --top-module tb_dhobs -GMUT=${MUT:-0} -Mdir $O/obj \
  rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv rtl/qwen_split/mu/qfd_sys_face_mu_dhobs.sv \
  results/rtl/mu_qwen_1018/dhobs/tb_dhobs.sv > $O/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $O/build.log; exit 2; }
$O/obj/Vtb_dhobs "$@" > $O/run.out 2>&1; cat $O/verilator_version.txt; grep TB_DHOBS $O/run.out
