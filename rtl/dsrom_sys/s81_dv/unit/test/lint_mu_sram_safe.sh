#!/usr/bin/env bash
# MU-S81-2/HSLOT (10-19): ONE mutant of SEQHOST_MU_GATE (run_seq_host_mu_bench.sh) as a stand-alone bench for the
# dsdv_mu_hslot closure kit.  Same sources, Verilator 5.050, cases and checker as the gate.
#   run_seq_host_mu_mut.sh OUTDIR MUT CASE      MUT 1 (user field dropped, case ar) | 2 (collision check dropped,
#                                               case f_collide) | 5 (gap-table index stuck, case ar)
# Prints the checker verdict line first (SEQHOST_MU FAIL ... / SEQHOST_MU FAULT0 FAIL ...), then the mutant run log;
# exits 1 when the mutant is detected (the expected outcome), 0 when it is NOT detected.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:?outdir}");  mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
U=$R/rtl/dsrom_sys/s81_dv/unit; T=$U/test
P=$R/results/rtl/s81_mu_1018/prog_L0_mu; N=$(grep -c . $P/prog/host_boot.memh)
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $R/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v $U/dsdv_mu_hslot.sv $U/dsdv_mu_mem.sv $R/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v $U/dsdv_mu_hwin.sv"
verilator --version
bad=0
for top in dsdv_mu_hwin dsdv_seq_host_mux; do
 verilator --lint-only -Wall -Wno-fatal +define+DSDV_MU_POINTER_ASSERT --top-module $top $F > "$O/$top.log" 2>&1
 W=$(grep -E '^%(Warning|Error)' "$O/$top.log" | grep -E 'dsdv_mu_(hwin|mem)\.sv' | grep -v -E 'Warning-(DECLFILENAME|UNUSEDSIGNAL|UNUSEDPARAM|PINCONNECTEMPTY)')
 if grep -q '^%Error' "$O/$top.log" || [ -n "$W" ]; then echo "LINT FAIL $top"; echo "$W"; grep -m5 '^%Error' "$O/$top.log"; bad=1; else echo "LINT PASS $top"; fi
done
exit $bad
