#!/usr/bin/env bash
# LEAD2-S81/MU kit bench of HWIN21c = dsdv_mu_hwin_capture_1019 EARLY_HEAD_CAPTURE=1 (the synthesized DUT bytes are
# identical to rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin_capture*_1019.sv) cycle-mitered every cycle against the frozen
# anchor dsdv_mu_hwin 1e057 (EARLY_HEAD_CAPTURE=0) beside the CLOSED dsdv_mu_hslot, exactly as the private package
# campaign (tools/hwin_private_package_1019, run_mu_hwin_early_capture.sh). Verilator 5.050 (daemon version).
# Usage (cwd = repo root): run_c21_bench.sh OUTDIR {ns47|ns2|mut2|wrap}
#  ns47 / ns2: MUWIN PASS (no EARLY_MITER / EARLY_X fatal). mut2: early-capture mechanism mutant EC_MUT=2,
#  wrap: NEXT_WRAP_MUTANT -- both must stop with an EARLY_MITER fatal.
set -u
O=$(realpath -m "$1"); V=$2; mkdir -p "$O"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
S=tools/hwin_private_package_1019/sim; U=$S/rtl/dsrom_sys/s81_dv/unit
files=("$S/rtl/lib/ot_rst_relay.sv" "$S/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv"
 "$S/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$S/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v"
 "$U/dsdv_mu_hslot.sv" "$U/dsdv_mu_mem.sv" "$U/dsdv_mu_mem_early_capture.sv" "$U/dsdv_mu_hwin.sv"
 "$U/dsdv_mu_hwin_capture_1019.sv" "$U/dsdv_mu_hwin_capture_mem_1019.sv" "$U/dsdv_mu_hwin_capture_early_1019.sv" "$U/test/tb_dsdv_mu_hwin_early_capture.sv")
for f in dsdv_mu_hwin_capture_1019 dsdv_mu_hwin_capture_mem_1019 dsdv_mu_hwin_capture_early_1019; do
  cmp -s "$U/$f.sv" "rtl/dsrom_sys/s81_dv/unit/$f.sv" || { echo "DUT_SOURCE_MISMATCH $f"; exit 3; }; done
case $V in
 ns47) D=(+define+NSLOT_TEST=47 +define+MIN_D);;
 ns2)  D=(+define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D);;
 mut2) D=(+define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+EC_MUT=2);;
 wrap) D=(+define+NSLOT_TEST=2 +define+MIN_D +define+SWEEP256 +define+LONG_D +define+NEXT_WRAP_MUTANT);;
 *) echo "unknown variant $V"; exit 2;;
esac
verilator --version | tee "$O/verilator_version.txt"
verilator --binary --timing --x-initial unique --x-assign unique -j "${J:-4}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
  +define+OT_MEM_NO_INIT --top-module tb_dsdv_mu_hwin_early_capture "${D[@]}" "${files[@]}" \
  --Mdir "$O/obj" -o tb > "$O/build.log" 2>&1 || { echo "BUILD_FAIL $V"; tail -20 "$O/build.log"; exit 1; }
rc=0
"$O/obj/tb" +verilator+rand+reset+2 +verilator+seed+1 +reset_phase=0 +rx_shift=-1 +release_word_stage=1 > "$O/run.log" 2>&1 || rc=$?
cat "$O/run.log"; echo "TB_RC $rc"
[ $rc -eq 0 ] && grep -q '^MUWIN PASS' "$O/run.log"
