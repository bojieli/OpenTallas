#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$PWD;W=$R/${FAN32_NATIVE_OUT:-wrapper_native};mkdir -p "$W"
cat > "$W/prove.ys" <<'YS'
read_liberty -lib /tmp/lib/SIMPLE.lib
read_liberty -lib /tmp/lib/AO.lib
read_liberty -lib /tmp/lib/OA.lib
read_liberty -lib /tmp/lib/INVBUF.lib
read_liberty -lib /tmp/lib/SEQ.lib
read_verilog -sv /src/rtl/hdc/ot_hdc_fp32_add_lat.sv /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv /src/rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v
hierarchy -check -top ot_hdc_fp32_add_lat_fan32 -chparam LAT 7 -chparam DRST 0 -chparam SAFE_DIST 1
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top ot_hdc_fp32_add_lat_fan32 -flatten -noshare
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
write_verilog -noattr /out/retained.v
write_json /out/retained.json
stat
YS
docker image inspect openroad/orfs:latest --format '{{.Id}}' > "$W/image.id"
docker run --rm -v "$R:/src:ro" -v "$W:/out" openroad/orfs:latest bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null
N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM;mkdir -p /tmp/lib
for k in SIMPLE AO OA;do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib;done
zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
sha256sum /tmp/lib/*.lib > /out/libraries.sha256
yosys -l /out/synth.log -s /out/prove.ys
' > "$W/stdout.log" 2>&1
python3 tools/textbook_lint.py check --netlist "$W/retained.v" --out "$W/native32.json" --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$W/native32.log" 2>&1
