#!/usr/bin/env bash
# Run via ot-run on a staged source tree. Baseline plus three integrity mutants.
set -euo pipefail
cd "$(dirname "$0")/../../../.."
out=$(realpath -m "${1:-/tmp/wb-kshare-bench}")
mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
n=rtl/hbm_accel/loader/service_native
src=("$n/tb_hbm_svc_wb_kshare_splitstrap_q.sv" "$n/ot_hbm_svc_wb_kport.sv" "$n/ot_hbm_svc_vm_kshare_splitstrap.sv" "$n/ot_hbm_svc_ring_h9b_ff.sv"
 "$n/ot_hbm_svc_wb_cutthrough_cdc.sv" "$n/ot_hbm_svc_async_fifo.sv"
 "$n/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$n/ot_hbm_svc_pc_ctrl_leaf.sv" "$n/ot_hbm_svc_pc_ctrl_leaf_cfg.sv"
 "$n/tb_hbm_svc_command_dram_pipeline_fixture.sv" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv
 rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${src[@]}" > "$out/source.sha256"
cases=("${@:2}")
if ((${#cases[@]}==0)); then cases=(baseline streamstrap hbmstrap); fi
for c in "${cases[@]}"; do
 args=()
 # raw_<case> (HBMA-SVC 10-17): build the mutant <case> but judge it as a baseline, so a mutant bench exits non-zero
 # (closure-loop "expect": "fail") and prints its assertion line
 raw=0; if [[ "$c" == raw_* ]]; then raw=1; c=${c#raw_}; fi
 case "$c" in streamstrap) args=(-GKSMUT=8);; hbmstrap) args=(-GKSMUT=7);; overlap) args=(-GKSMUT=3);; address) args=(-GKSMUT=4);; premature) args=(-GWBMUT=1);; esac
 "$vl" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_hbm_svc_wb_kshare_splitstrap_q --Mdir "$out/obj-$c" -o sim "${args[@]}" "${src[@]}" > "$out/build-$c.log" 2>&1
 rc=0
 "$out/obj-$c/sim" > "$out/$c.log" 2>&1 || rc=$?
 if ((raw)); then
  echo "RAW $c rc=$rc"; grep -E 'WB_INTEGRITY|^PASS' "$out/$c.log" | head -3 || true
  if [[ "$rc" != 0 ]] || ! grep -q '^PASS tb_hbm_svc_wb_kshare_splitstrap_q' "$out/$c.log"; then echo "RAW_FAIL $c"; rm -rf "$out/obj-$c"; exit 1; fi
 elif [[ "$c" == baseline ]]; then
  test "$rc" = 0 && grep -q '^PASS tb_hbm_svc_wb_kshare_splitstrap_q' "$out/$c.log"
 else
  test "$rc" != 0 && grep -q 'WB_INTEGRITY' "$out/$c.log"
 fi
 # SVC-SMALL 10-18: surface the tb verdict/count lines on stdout (the closure loop reads only this output;
 # without them a qualified run had no count line -> VACUOUS)
 grep -E '^PASS tb_hbm_svc_wb_kshare_splitstrap_q' "$out/$c.log" | head -3 || true
 echo "QUALIFIED $c expected_exit=$rc"
 # Keep source-bound logs; generated C++ and objects are disposable after the verdict.
 rm -rf "$out/obj-$c"
done
