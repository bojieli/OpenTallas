#!/usr/bin/env bash
# EPYC-only changed-source gate. No physical launch; BW0 history is not replayed.
set -uo pipefail
out=$1
mkdir "$out" || exit 3
git rev-parse HEAD > "$out/source_commit.txt"
python3 tools/qwen_slab_capture_contract.py --out "$out/model.json"
for case in 0:0:7 170:3:2 490:5:4 830:7:0; do
  IFS=: read -r phase data_seed credit_seed <<< "$case"
  iverilog -g2012 -s tb_qwen_slab_port_group_capture \
    -P tb_qwen_slab_port_group_capture.PHASE_PS=$phase \
    -P tb_qwen_slab_port_group_capture.DATA_SEED=$data_seed \
    -P tb_qwen_slab_port_group_capture.CREDIT_SEED=$credit_seed \
    -o "$out/gate_$phase.vvp" rtl/test/tb_qwen_slab_port_group_capture.sv \
    rtl/physical/ot_qwen_slab_port_group_capture.sv rtl/common/ot_meso_fifo.sv \
    rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fpu.sv \
    rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
    > "$out/build_$phase.log" 2>&1
  rc=$?; echo "$rc" > "$out/build_$phase.exit"
  if [ "$rc" != 0 ]; then exit "$rc"; fi
  vvp "$out/gate_$phase.vvp" > "$out/gate_$phase.log" 2>&1
  rc=$?; echo "$rc" > "$out/gate_$phase.exit"
  if [ "$rc" != 0 ] || grep -q FAIL "$out/gate_$phase.log" || ! grep -q 'RESET EPOCH PASS' "$out/gate_$phase.log"; then exit 86; fi
done
