#!/usr/bin/env bash
# REFILL-0730/HWIN kit bench of dsdv_mu_hwin (one variant per call, for the ref_tile job's bench stages): the leaf beside
# the CLOSED dsdv_mu_hslot on tb_dsdv_mu_hwin (Verilator from PATH; the closure daemon pins 5.050).
# Usage: run_mu_hwin_kit_bench.sh OUTDIR {base|badrt|mut3|mut4}   (cwd = repo root)
# base: "MUWIN PASS"; badrt: "MUWIN BADRT PASS (fault raised)"; mut3 / mut4 (RTL mutants) print MUWIN FAIL + ERR lines.
set -u
O=$(realpath -m "$1"); V=$2; mkdir -p "$O"
U=rtl/dsrom_sys/s81_dv/unit
case $V in base) D=();; badrt) D=(+define+BADRT=1);; mut3) D=(+define+WMUT=3);; mut4) D=(+define+WMUT=4);;
  *) echo "unknown variant $V"; exit 2;; esac
verilator --version
verilator --binary --timing +define+DSDV_MU_POINTER_ASSERT -j "${J:-2}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_dsdv_mu_hwin "${D[@]}" \
  rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v $U/dsdv_mu_mem.sv physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v $U/dsdv_mu_hslot.sv $U/dsdv_mu_hwin.sv $U/test/tb_dsdv_mu_hwin.sv \
  --Mdir "$O/obj" -o tb > "$O/build.log" 2>&1 || { echo "BUILD_FAIL $V"; tail -20 "$O/build.log"; exit 1; }
"$O/obj/tb" | tee "$O/run.log"
grep -q -E '^MUWIN (BADRT )?PASS' "$O/run.log"
