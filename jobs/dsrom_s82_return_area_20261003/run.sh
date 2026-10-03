#!/usr/bin/env bash
set -euo pipefail
source "$HOME/.opentallas-env"
job_dir="$1"
cd "$job_dir"
sha256sum -c source.sha256
lib_dir="$HOME/.local/opentallas-pdk-asap7/lib/NLDM"
seq_lib="$lib_dir/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
inv_lib="$lib_dir/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib"
simple_lib="$lib_dir/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib"
sha256sum "$seq_lib" "$inv_lib" "$simple_lib" > library.sha256
yosys -V > tool_identity.txt
cat > map.ys <<YS
read_liberty -lib $seq_lib
read_liberty -lib $inv_lib
read_liberty -lib $simple_lib
read_slang --top ot_v41_retn_w17w10 -G RD=64 -G RST=1 -G BYPASS=1 source/rtl/v41rom/ot_v41_ret.sv source/rtl/v41die/ot_v41_retn_w17w10.sv source/rtl/proto/ot_fp32_add_rne_pipe.sv source/rtl/hdc/ot_hdc_delay.sv
synth -top ot_v41_retn_w17w10 -flatten -noabc
dfflibmap -liberty $seq_lib
abc -g NAND
techmap -map native_map.v
clean
check
write_json mapped.json
write_verilog -noattr mapped.v
stat
YS
set +e
/srv/opentallas-scratch/admit.sh 16 -- yosys -T -l mapped.log map.ys
status=$?
set -e
printf '%s\n' "$status" > exit.rc
sha256sum -c source.sha256 > source_after.txt
exit "$status"
