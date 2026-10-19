#!/bin/bash
set -euo pipefail
cd run
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 4 -Wno-fatal --top-module tb_qwen_typed_su_observer -Mdir typed_obs_obj ../src/rtl/qwen_dv/qfd_dv_typed_su_observer.sv ../src/rtl/test/qwen_dv/tb_qwen_typed_su_observer.sv > typed_obs_build.log 2>&1
typed_obs_obj/Vtb_qwen_typed_su_observer "+EVENTS=$PWD/typed_observer_events.txt" > typed_obs_nominal.log
set +e
typed_obs_obj/Vtb_qwen_typed_su_observer "+EVENTS=$PWD/typed_observer_events.txt" +MUT=1 > typed_obs_wire_mut.log 2>&1
rc=$?
set -e
test "$rc" != 0
grep TYPED_SU_OBSERVER_PASS typed_obs_nominal.log
grep TYPED_SU_OBSERVER_FAIL typed_obs_wire_mut.log
