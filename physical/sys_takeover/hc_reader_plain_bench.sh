#!/bin/bash
# sys-takeover 2026-10-09: committed HC reader gate (tb_hc_mean_capture HC_VM_READER + HC_DISTRIBUTED, synthetic
# full-shape vectors and the four bad-native-read negatives) on the PROTECT=0 plain reader.
#   hc_reader_plain_bench.sh pos|neg OUT
set -uo pipefail
mode=$1; out=$2; mkdir -p "$out"
src=(rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_secded_pipe.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv ${HC_READER_SRC:-rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_input_reader.sv} rtl/common/ot_sc_pfifo.sv
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_seed_join.sv "$out/tb.sv")
# the VM model keys its rows on the capture of the command the reader is serving (queue of accepted commands, popped
# at each command's first read), not the bench's next command register, which a registered-boundary reader accepts early: identical for the bare reader, required for the wrapped one
python3 - "$out" <<'PY'
import sys,pathlib
t=pathlib.Path('rtl/test/dsrom_hc_capture_20261009/tb_hc_mean_capture.sv').read_text()
a="response_q[32*i_vm+:32]={inputs[cmd_capture*160+"
assert t.count(a)==1
t=t.replace(a,"response_q[32*i_vm+:32]={inputs[vm_cap*160+")
b="    always @(posedge clk) if(req_valid&&req_ready) begin"
assert t.count(b)==1
t=t.replace(b,"    reg [1:0] vm_cap=0;reg [1:0] cq[0:15];integer cqw=0,cqr=0;\n    always @(posedge clk) if(cmd_valid&&cmd_ready) begin cq[cqw%16]<=cmd_capture;cqw<=cqw+1;end\n"+b)
c="row_vm=(req_row-512)%320-rank*80;"
assert t.count(c)==1
t=t.replace(c,c+"\n        if(copy_vm==0&&row_vm==0) begin vm_cap=cq[cqr%16];cqr=cqr+1;end")
pathlib.Path(sys.argv[1],'tb.sv').write_text(t)
PY
iverilog -g2012 -DHC_READER_PLAIN -s tb_hc_mean_capture -DHC_VM_READER -DHC_DISTRIBUTED -o "$out/reader.vvp" "${src[@]}" >"$out/elaborate.log" 2>&1 || { cat "$out/elaborate.log"; echo HCRP_BENCH_ERROR; exit 2; }
python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/synthetic" >"$out/vectors.log" 2>&1 || { echo HCRP_BENCH_ERROR vectors; exit 2; }
if [[ $mode == pos ]]; then
  vvp "$out/reader.vvp" +vectors="$out/synthetic" >"$out/reader.log" 2>&1; rc=$?; tail -3 "$out/reader.log"
  if [[ $rc == 0 ]] && ! grep -qi fatal "$out/reader.log"; then echo HC_READER_PLAIN_PASS; exit 0; fi
  echo HC_READER_PLAIN_FAIL; exit 1
fi
n=0
for bad in 6 7 8 10; do
  vvp "$out/reader.vvp" +vectors="$out/synthetic" +bad="$bad" >"$out/negative_$bad.log" 2>&1 && { echo "bad $bad ESCAPED"; exit 0; }
  grep -q 'native H reader fault' "$out/negative_$bad.log" && n=$((n+1))
done
[[ $n == 4 ]] && { echo "HC_READER_PLAIN_NEG_DETECTED 4/4"; exit 1; }
echo "HC_READER_PLAIN_NEG_UNCLEAR $n/4"; exit 0
