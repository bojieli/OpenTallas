#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$(pwd);G=$R/graph;A=results/rtl/fp32_add_native_clone_1020
mkdir -p "$G"
cat > "$G/base.ys" <<'YS'
read_verilog -sv /src/rtl/hdc/ot_hdc_fp32_add_lat.sv /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/results/rtl/fp32_add_native_clone_1020/probe.sv
hierarchy -top fan32_graph_input
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top fan32_graph_input -flatten -noshare
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
write_verilog -noattr /out/mapped.v
read_liberty -lib /tmp/lib/SIMPLE.lib
read_liberty -lib /tmp/lib/AO.lib
read_liberty -lib /tmp/lib/OA.lib
read_liberty -lib /tmp/lib/INVBUF.lib
read_liberty -lib /tmp/lib/SEQ.lib
hierarchy -check -top fan32_graph_input
write_json /out/mapped.json
YS
docker image inspect openroad/orfs:latest --format '{{.Id}}' > "$G/image.id"
docker run --rm -v "$R:/src:ro" -v "$G:/out" openroad/orfs:latest bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null
N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM;mkdir -p /tmp/lib
for k in SIMPLE AO OA;do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib;done
zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
sha256sum /tmp/lib/*.lib > /out/libraries.sha256
yosys -l /out/base.log -s /out/base.ys
for k in SIMPLE AO OA INVBUF SEQ;do echo "read_liberty -ignore_miss_func /tmp/lib/$k.lib";done > /out/models.ys
echo "write_verilog -noattr /out/cells.v" >> /out/models.ys
yosys -l /out/models.log -s /out/models.ys
' > "$G/base.stdout" 2>&1
python3 "$A/svc7_bound_graph.py" "$G/mapped.json" --top fan32_graph_input --name ot_hdc_fp32_add_lat7_fan32_native --out "$G/native.v" --limit 24 > "$G/replicate.log" 2>&1
cat > "$G/retained.ys" <<'YS'
read_liberty -lib /tmp/lib/SIMPLE.lib
read_liberty -lib /tmp/lib/AO.lib
read_liberty -lib /tmp/lib/OA.lib
read_liberty -lib /tmp/lib/INVBUF.lib
read_liberty -lib /tmp/lib/SEQ.lib
read_verilog /out/native.v
hierarchy -check -top ot_hdc_fp32_add_lat7_fan32_native
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top ot_hdc_fp32_add_lat7_fan32_native -flatten -noshare
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
write_verilog -noattr /out/retained.v
write_json /out/retained.json
YS
docker run --rm -v "$R:/src:ro" -v "$G:/out" openroad/orfs:latest bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null
N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM;mkdir -p /tmp/lib
for k in SIMPLE AO OA;do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib;done
zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
yosys -l /out/retained.log -s /out/retained.ys
' > "$G/retained.stdout" 2>&1
python3 tools/textbook_lint.py check --netlist "$G/retained.v" --out "$G/native32.json" --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$G/native32.log" 2>&1
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version > "$G/verilator.version"
"$VL" --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_fp32_add_fan32 -Mdir "$G/obj" -o sim "$G/native.v" "$G/cells.v" "$A/wrapper.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/test/hdc/tb_fp32_add_fan32.sv > "$G/build.log" 2>&1
"$G/obj/sim" +verilator+rand+reset+2 +verilator+seed+15 > "$G/run_seed15.log" 2>&1
"$G/obj/sim" +verilator+rand+reset+2 +verilator+seed+51 > "$G/run_seed51.log" 2>&1
tail -5 "$G/run_seed15.log"
