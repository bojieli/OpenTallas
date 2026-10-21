#!/usr/bin/env bash
# PL-SEQ option B: the S81U-SEQ golden bench (run_seq_host_bench.sh, unchanged tb) on dsdv_seq_host_bw = the hardened core
# dsdv_seq_host_c + the 2-stage die-lane stand-in.  The tb is copied with its DUT module name swapped (dsdv_seq_host ->
# dsdv_seq_host_bw) and its dut.u_l<k> probes re-rooted to dut.u_c.u_l<k>; nothing else changes.  Goldens seeds 1-4 PASS, collide / W-drop faults, mutants 1..9 FAIL
# (S81-GUSEQ 10-18: 7 OT_ING_MUT_HREGV, 8 OT_ING_MUT_RAC = APIPE 7 ingest; 9 = lk RL 1 rung landing dropped; as run_seq_host_bench.sh).
# S81-SHP 10-19: + ot_dsdv_walk_issue.sv (sq SRAM walker), pair seeds, mutant 10 (as run_seq_host_bench.sh).
# Run on the FLEET (ot-run), never on localhost.  Prints SEQHOST_C_GATE PASS/FAIL.   Usage: run_seq_host_c_bench.sh OUTDIR [seeds]
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=${1:-$(mktemp -d)}; SEEDS=${2:-"1 2 3 4"}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
U=$R/rtl/dsrom_sys/s81_dv/unit
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv
   $R/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $U/dsdv_seq_host_c.sv $U/test/dsdv_seq_host_bw.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
grep -c 'dsdv_seq_host #(' "$U/test/tb_dsdv_seq_host.sv" | grep -qx 1 || { echo "tb DUT instance not unique"; exit 2; }
sed -e 's/\bdsdv_seq_host #(/dsdv_seq_host_bw #(/' -e 's/\bdut\.u_l\([012]\)\b/dut.u_c.u_l\1/g' "$U/test/tb_dsdv_seq_host.sv" > "$O/tb_dsdv_seq_host_c.sv"
build() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +define+DSFD_HOST_C_STATIC \
    --top-module tb_dsdv_seq_host "$@" --Mdir "$O/$l" -o tb $F "$O/tb_dsdv_seq_host_c.sv" > "$O/build_$l.log" 2>&1 \
    || { echo "BUILD_FAIL $l (see $O/build_$l.log)"; return 2; }
}
bad=0
build base || exit 2
for s in $SEEDS; do
  "$O/base/tb" +seed=$s > "$O/run_s$s.log" 2>&1
  grep '^SEQHOST seed' "$O/run_s$s.log"; grep -q '^SEQHOST PASS' "$O/run_s$s.log" || { echo "golden seed $s FAIL"; bad=1; }
done
for s in $SEEDS; do   # S81-SHP 10-19: sq = SRAM walker (ot_dsdv_walk_issue): two calendar rows on one edge, as run_seq_host_bench.sh
  "$O/base/tb" +seed=$s +pair=1 > "$O/run_pair_s$s.log" 2>&1
  echo "PAIR $(grep '^SEQHOST seed' "$O/run_pair_s$s.log")"; grep -q '^SEQHOST PASS' "$O/run_pair_s$s.log" || { echo "golden pair seed $s FAIL"; bad=1; }
done
"$O/base/tb" +seed=7 +collide=1 > "$O/run_collide.log" 2>&1
grep '^SEQHOST COLLIDE' "$O/run_collide.log"; grep -q 'PASS (fault raised)' "$O/run_collide.log" || { echo "collision not faulted"; bad=1; }
"$O/base/tb" +seed=3 +stdrop=1 > "$O/run_stdrop.log" 2>&1
grep '^SEQHOST STDROP' "$O/run_stdrop.log"; grep -q 'PASS (fault raised)' "$O/run_stdrop.log" || { echo "W region drop not faulted"; bad=1; }
mdef() { case $1 in 7) echo +define+OT_ING_MUT_HREGV;; 8) echo +define+OT_ING_MUT_RAC;; *) echo +define+MUT=$1;; esac; }
for m in 1 2 3 4 5 6 7 8 9 10; do
  build mut$m $(mdef $m) || { bad=1; continue; }
  "$O/mut$m/tb" +seed=1 > "$O/run_mut$m.log" 2>&1
  if grep -q '^SEQHOST PASS' "$O/run_mut$m.log"; then echo "mutant $m NOT detected"; bad=1
  else echo "mutant $m detected: $(grep -m1 '^SEQHOST seed' "$O/run_mut$m.log" | grep -o 'mism.*')"; fi
done
verilator --lint-only -Wall -Wno-fatal --top-module dsdv_seq_host_c $F > "$O/lint.log" 2>&1
W=$(grep '^%Warning' "$O/lint.log" | grep 'unit/dsdv_seq_host_c.sv' | grep -v -E 'Warning-(DECLFILENAME|PINCONNECTEMPTY|UNUSEDSIGNAL)' | grep -v -E "MULTIDRIVEN.*'s_hw(_[we])?'")
if grep -q '^%Error' "$O/lint.log" || [ -n "$W" ]; then echo "lint FAIL (see $O/lint.log): $W"; bad=1
else echo "lint clean: dsdv_seq_host_c.sv 0 errors, 0 unwaived warnings (waivers as dsdv_seq_host)"; fi
[ $bad = 0 ] && echo "SEQHOST_C_GATE PASS" || echo "SEQHOST_C_GATE FAIL"
exit $bad
