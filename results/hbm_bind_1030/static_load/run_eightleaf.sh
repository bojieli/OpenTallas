#!/usr/bin/env bash
set -eu
# Run from this directory after supplying unchanged native_load_static.sv and
# its unchanged 128x256 SRAM model as sram.v from the pinned source closure.
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_static_load_eightleaf ot_hbm_static_load_quad_vehicle.sv tb_static_load_eightleaf.sv native_load_static.sv sram.v --Mdir obj > build.log 2>&1
./obj/Vtb_static_load_eightleaf > eightleaf_baseline.log 2>&1
set +e
./obj/Vtb_static_load_eightleaf +MUT_RELEASE=1 > eightleaf_release_mutant.log 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]
grep -q EIGHTLEAF_OWNER_FAILURE eightleaf_release_mutant.log
echo PASS_EIGHTLEAF_BASELINE_AND_RELEASE_MUTANT
