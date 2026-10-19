#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:?output directory required}")
# Atomic refusal happens before any receipt, object, version or log is written.
if ! mkdir "$O"; then echo "REFUSE existing output $O" >&2; exit 73; fi
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
U="$R/rtl/dsrom_sys/s81_dv/unit"
files=("$R/rtl/lib/ot_rst_relay.sv" "$R/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v"
 "$U/dsdv_mu_hslot.sv" "$U/dsdv_mu_mem.sv" "$U/dsdv_mu_mem_early_capture.sv" "$U/dsdv_mu_hwin.sv"
 "$U/test/tb_dsdv_mu_hwin_early_capture.sv" "$U/test/tb_dsdv_mu_mem_early_capture.sv")
sha256sum "${files[@]}" > "$O/sources.sha256"
verilator --version > "$O/verilator_version.txt"
grep -q 'Verilator 5.050' "$O/verilator_version.txt"
run() {
 local name=$1 top=$2 expected=$3; shift 3
 local case_dir="$O/$name"
 mkdir "$case_dir" || { echo "REFUSE existing case $case_dir" >&2; exit 73; }
 printf '%s\n' "$@" > "$case_dir/arguments.txt"
 verilator --binary --timing --x-initial unique --x-assign unique -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
  +define+OT_MEM_NO_INIT --top-module "$top" "$@" "${files[@]}" \
  --Mdir "$case_dir/obj" -o tb > "$case_dir/build.log" 2>&1
 for seed in ${RUN_SEEDS:-1 19 313}; do
  local rc=0
  "$case_dir/obj/tb" +verilator+rand+reset+2 +verilator+seed+$seed > "$case_dir/run_seed$seed.log" 2>&1 || rc=$?
  if [[ "$expected" == FAIL:* ]]; then
    [[ $rc -ne 0 ]]; grep -q "${expected#FAIL:}" "$case_dir/run_seed$seed.log"
  else
    [[ $rc -eq 0 ]]; grep -q "$expected" "$case_dir/run_seed$seed.log"
  fi
 done
}
RUN_SEEDS=1 run original_assert_repro tb_dsdv_mu_hwin_early_capture 'FAIL:event boot count differs event0' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+ANCHOR_ONLY_REPRO +define+ORIGINAL_ASSERT_REPRO +define+DSDV_MU_POINTER_ASSERT
RUN_SEEDS=1 run guarded_assert_corruption tb_dsdv_mu_hwin_early_capture 'FAIL:event boot count differs event0' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+ANCHOR_ONLY_REPRO +define+ASSERT_CORRUPT
run ns2_ev1 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D
run ns47 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=47 +define+MIN_D
printf '%s\n' 'EARLY_CAPTURE_INITIAL PASS'
