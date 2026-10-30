#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_current_publication --Mdir obj -f source_middle.f src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop_xo.sv native_bound_middle_fixture.sv tb_current_publication.sv >build.log 2>&1
rc=$?;echo BUILD_RC=$rc >>status.txt
if [ "$rc" -ne 0 ];then tail -18 build.log;exit "$rc";fi
obj/Vtb_current_publication >candidate.log 2>&1
rc=$?;echo CANDIDATE_RC=$rc >>status.txt
obj/Vtb_current_publication +legacy >legacy.log 2>&1
lrc=$?;echo LEGACY_RC=$lrc >>status.txt
obj/Vtb_current_publication +mutant >mutant.log 2>&1
mrc=$?;echo MUTANT_RC=$mrc >>status.txt
cat status.txt
if [ "$rc" -eq 0 ] && [ "$lrc" -ne 0 ] && [ "$mrc" -ne 0 ];then echo GATE_PASS >>status.txt;else exit 1;fi
