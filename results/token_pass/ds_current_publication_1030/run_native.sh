#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_current_publication --Mdir obj_native -f source_middle.f src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv native_bound_middle_fixture.sv tb_current_native.sv >native_build.log 2>&1
rc=$?;echo BUILD_RC=$rc >>native_status.txt
if [ "$rc" -ne 0 ];then tail -18 native_build.log;exit "$rc";fi
obj_native/Vtb_current_publication >native_candidate.log 2>&1
rc=$?;echo CANDIDATE_RC=$rc >>native_status.txt
obj_native/Vtb_current_publication +legacy >native_legacy.log 2>&1
lrc=$?;echo LEGACY_RC=$lrc >>native_status.txt
obj_native/Vtb_current_publication +mutant >native_mutant.log 2>&1
mrc=$?;echo MUTANT_RC=$mrc >>native_status.txt
cat native_status.txt
if [ "$rc" -eq 0 ] && [ "$lrc" -ne 0 ] && [ "$mrc" -ne 0 ];then echo GATE_PASS >>native_status.txt;else exit 1;fi
