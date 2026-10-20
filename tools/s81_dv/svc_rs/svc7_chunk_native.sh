#!/usr/bin/env bash
set -euo pipefail
G=$(cd "${1:?graph directory}" && pwd)
ROOT=$PWD
TOP=${3:-ot_s81svc7_chunk_reduce}
O=$G/${2:-chunk_native}
mkdir -p "$O"
cat > "$O/map.ys" <<'YS'
read_verilog -lib /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v
read_verilog -sv /graph/native.v /src/rtl/hdc/v41x/ot_s81svc7_chunk_reduce.sv /src/rtl/hdc/v41x/ot_s81svc7_skew_sram.sv /src/rtl/hdc/v41x/ot_s81svc7_chunk_core.sv /src/rtl/hdc/v41x/ot_s81svc7_bmul_native.v
YS
for k in SIMPLE AO OA INVBUF SEQ;do echo "read_liberty -lib /tmp/lib/$k.lib" >> "$O/map.ys";done
cat >> "$O/map.ys" <<'YS'
hierarchy -check -top ot_s81svc7_chunk_reduce
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top ot_s81svc7_chunk_reduce -flatten -noshare
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
write_verilog -noattr /out/mapped.v
write_json /out/mapped.json
YS
sed -i "s/-top ot_s81svc7_chunk_reduce/-top $TOP/g" "$O/map.ys"
docker run --rm -v "$ROOT:/src:ro" -v "$G:/graph:ro" -v "$O:/out" openroad/orfs:latest bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
 mkdir -p /tmp/lib /out/lib
 for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
 zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
 cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
 cp /tmp/lib/*.lib /out/lib/
 cp /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_tt.lib /out/lib/MACRO.lib
 sha256sum /out/lib/*.lib /src/physical/common_flow/ot_keep_regs.tcl /src/rtl/hdc/v41x/ot_s81svc7_chunk_reduce.sv /src/rtl/hdc/v41x/ot_s81svc7_skew_sram.sv /src/rtl/hdc/v41x/ot_s81svc7_chunk_core.sv /src/rtl/hdc/v41x/ot_s81svc7_bmul_native.v /graph/native.v > /out/source_identity.sha256
 yosys -V > /out/tool_identity.txt
 yosys-abc -c version >> /out/tool_identity.txt
 yosys -l /out/synth.log -s /out/map.ys
' > "$O/synth.stdout" 2>&1
args=();for f in "$O"/lib/*.lib;do args+=(--liberty "$f");done
python3 tools/ref_tile/native_census.py --netlist "$O/mapped.v" --top "$TOP" --out "$O/census.json" "${args[@]}" > "$O/census.log" 2>&1
python3 tools/s81_dv/svc_rs/svc7_chunk_stats.py "$O" "$TOP"
