#!/usr/bin/env bash
# H-NETLIST/attn 2026-10-16 benches (iverilog -g2012). usage: run_attn_0030.sh OUT
#  xcal : ot_hbm_svc_sm_xcal lockstep vs the actual svg go path (ot_hbm_svc_sm_issuer FIXED_GO + ot_smh_calendar_static
#         W135); MUT0 PASS, MUT1 (one edge late) / MUT2 (field swap) FAIL.
#  argmax_vm : ot_hbm_argmax_static_sw_vm vs ot_hbm_argmax_static_sw, random records on a fixed-latency VM/record-client
#         model (RD 7, ACK 11 edges); MUT0 PASS, MUT1 (STREAM record passes through: hangs) / MUT2 (all records illegal) FAIL.
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); mkdir -p "$out"; rc=0
X=(rtl/test/hbm_netlist_v16/tb_hbm_svc_sm_xcal.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal.sv
   rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_issuer.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
   physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
A=(rtl/test/hbm_netlist_v16/tb_argmax_sw_vm.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv
   rtl/hbm_accel/generic/ot_hbm_argmax_static_sw.sv rtl/hbm_accel/generic/ot_hbm_argmax_static.sv
   physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
   physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
   rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
check() {  # name mut log expect(PASS|FAIL) marker
  if grep -q "$5 $4" "$3"; then echo "$1 MUT$2 $4 (expected)"; else echo "$1 MUT$2 UNEXPECTED"; rc=1; fi; }
for m in 0 1 2; do
  iverilog -g2012 -DMUT=$m -o "$out/x$m" "${X[@]}" && vvp -n "$out/x$m" > "$out/xcal_mut$m.log" 2>&1
  check xcal $m "$out/xcal_mut$m.log" $([ $m = 0 ] && echo PASS || echo FAIL) XCAL_LOCKSTEP
  iverilog -g2012 -DMUT=$m -DRD=7 -DACKD=11 -DNREC=300 -o "$out/a$m" "${A[@]}" && vvp -n "$out/a$m" > "$out/argmax_mut$m.log" 2>&1
  check argmax_vm $m "$out/argmax_mut$m.log" $([ $m = 0 ] && echo PASS || echo FAIL) ARGMAX_SW_VM
done
sha256sum "${X[@]}" "${A[@]}" > "$out/sources.sha256"
[ $rc = 0 ] && echo "ATTN_0030 BENCHES PASS" || echo "ATTN_0030 BENCHES FAIL"
exit $rc
