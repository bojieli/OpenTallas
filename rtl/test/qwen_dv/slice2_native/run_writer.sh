#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$HOME/.local/opentallas-tools/yosys-0.68/bin:$PATH"
verilator --version
mkdir -p out
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_writer --Mdir out/obj rtl/test/qwen_dv/slice2_native/tb_writer.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_split.sv rtl/common/landed_parent/ot_pl_land_n32.sv > out/build.log 2>&1
out/obj/Vtb_writer | tee out/pass.log
# The mutant writes the wrong next slot while keeping the reference calendar.
sed "s/{r\[D-2:0\], r\[D-1\]}/{r[0], r[D-1:1]}/" rtl/common/landed_parent/ot_pl_land_n32.sv > out/mut.sv
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_writer --Mdir out/mutobj rtl/test/qwen_dv/slice2_native/tb_writer.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_split.sv out/mut.sv > out/mutbuild.log 2>&1
set +e
out/mutobj/Vtb_writer > out/mut.log 2>&1
rc=$?
set -e
if [ "$rc" = 0 ]; then echo MUTANT_SURVIVED; exit 1; fi
grep -E 'LAND_FAULT|S2_WRITER FAIL' out/mut.log
printf 'WRITER_BENCH_COMPLETE\n'
