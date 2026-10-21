#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out/fixture"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$out/version.txt"
python3 - "$out/fixture" <<'FIX'
import json,sys
from pathlib import Path
r=json.load(open('results/rtl/tokfunc2_qw_1021/selected_station_tail_input/input.json'));o=Path(sys.argv[1])
(o/'pair.ev').write_text(''.join(f"{x['edge']} {x['port']} {x['word']}\n" for x in r['pair_pin_events']))
(o/'btab.ev').write_text(''.join(f"{x['edge']} {x['address']} {x['payload']}\n" for x in r['receiver_btab_stream_packets']))
(o/'cfg.hex').write_text('\n'.join(x['word'] for x in sorted(r['commands'],key=lambda x:x['slice']))+'\n')
for key,name in [('expected_sender_nb_data','sender'),('expected_receiver_scaled_data','receiver'),('receiver_scale_words','scale')]:
 (o/(name+'.hex')).write_text('\n'.join(r[key])+'\n')
FIX
srcs=(rtl/test/qwen_dv/s8/tb_selected_tail_pair.sv rtl/test/qwen_dv/s8/selected_tail_station.sv
 rtl/qwen_dv/s5/s8/qfd_dv_s8_station_tail1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_station_safe.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv
 rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv rtl/qwen_dv/qfd_dv_station_math_g.sv rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv
 rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_physical.sv rtl/common/landed_parent/ot_pl_land_n32.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
verilator --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_selected_tail_pair --Mdir "$out/obj" "${srcs[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_selected_tail_pair" +FIX="$out/fixture" > "$out/primary.log" 2>&1
cat "$out/primary.log"
