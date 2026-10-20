#!/usr/bin/env bash
set -euo pipefail
O=$(realpath "${1:?}");mkdir -p "$O/lib"
cp results/rtl/s81_l20rd_recovery_1020/native.ys "$O/native.ys"
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" -w /src openroad/orfs:latest bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
 for k in SIMPLE AO OA;do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /out/lib/$k.lib;done
 zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /out/lib/INVBUF.lib
 cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /out/lib/SEQ.lib
 yosys -V > /out/tool.txt
 yosys -l /out/synth.log -s /out/native.ys > /out/synth.stdout 2>&1
'
args=();for f in "$O"/lib/*.lib physical/ref_tile/ot_hdc_v41x_idx_hslice_m5/views/ot_hdc_v41x_idx_hslice/ot_hdc_v41x_idx_hslice_tt.lib physical/ref_tile/hidx_tail_native_rr/views/ot_hbm_idx_tail_native/ot_hbm_idx_tail_native_tt.lib physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib;do args+=(--liberty "$f");done
python3 tools/ref_tile/native_census.py --netlist "$O/mapped.v" --top idxrg_r32_native_top --out "$O/census.json" "${args[@]}" > "$O/census.log" 2>&1
