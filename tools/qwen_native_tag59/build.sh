#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?output};mkdir -p "$out";out=$(cd "$out"&&pwd)
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator";[[ -x "$v" ]]||v=$(command -v verilator)
cat > "$out/driver.cpp" <<'CPP'
#include "Vtb_coll_tp8_native59.h"
#include "verilated.h"
int main(int argc,char**argv){VerilatedContext ctx;ctx.commandArgs(argc,argv);Vtb_coll_tp8_native59 model(&ctx);model.clk=0;while(!ctx.gotFinish()){ctx.timeInc(416667);model.clk=!model.clk;model.eval();}model.final();return 0;}
CPP
sources=(rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/rom/ot_rom_oneshot_die_m.sv rtl/rom/ot_coll_fold_slice.sv rtl/rom/ot_coll_rst_leaf.sv rtl/rom/ot_coll_col_tile.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/lib/ot_hdly.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 rtl/rom/ot_rom_oneshot_allreduce.sv rtl/rom/ot_coll_tp8_die.sv rtl/rom/ot_coll_tp8_col_tile.sv rtl/rom/ot_rom_oneshot_die_native59.sv rtl/rom/ot_coll_tp8_die_native59.sv rtl/test/tb_coll_tp8_native59.sv)
sha256sum "${sources[@]}" "$out/driver.cpp" > "$out/source_pins.sha256"
"$v" --timescale-override 1ns/1fs --cc --exe --build -O1 -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-TIMESCALEMOD \
 ${NATIVE59_DEFINES:-} --top-module tb_coll_tp8_native59 -GWT=0 -GLATU=14 -GLATS=40 -GBPC=3600 -GICR=32 --Mdir "$out/obj" \
 "${sources[@]}" "$out/driver.cpp" -CFLAGS -O1 > "$out/build.log" 2>&1
sha256sum "$out/obj/Vtb_coll_tp8_native59" > "$out/executable.sha256"
echo "COLLECTIVE_PROVIDER_READY $out/obj/Vtb_coll_tp8_native59"
