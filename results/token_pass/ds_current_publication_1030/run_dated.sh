#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_current_publication --Mdir obj_dated -f source_middle.f src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv native_bound_middle_fixture.sv tb_current_dated.sv >dated_build.log 2>&1
rc=$?;echo BUILD_RC=$rc >>dated_status.txt
if [ "$rc" -ne 0 ];then tail -18 dated_build.log;exit "$rc";fi
obj_dated/Vtb_current_publication +release_book=inherited_rstd.hex >dated_inherited.log 2>&1
rc=$?;echo DATED_INHERITED_RC=$rc >>dated_status.txt
tail -8 dated_inherited.log
exit 0
