#!/usr/bin/env bash
# S81U-SEQ: dsdv_seq_host exact bench (lock-step vs the reused dsfd_host_c STATIC + ot_s81_fixed_issue goldens, SEEDS
# seeds), the illegal-collision run (must fault), the W-half region-live drop (must fault; RTL-BUILD-S81), 9 mutants
# that must FAIL (5: W svc half dropped from the merge, 6: host writes routed by the wrong PC bit, 7 / 8: see mdef), verilator lint.  Prints SEQHOST_GATE PASS/FAIL.
# Usage: run_seq_host_bench.sh [outdir] [seeds] [mutant 1..9: build + run that mutant only]
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
   $R/rtl/dsrom_sys/s81_dv/unit/host_sram/ot_dsdv_host_afifo_sram.sv
   $R/physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
build() { l=$1; shift
  verilator ${VL_EXTRA:-} --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +define+DSFD_HOST_C_STATIC \
    --top-module tb_dsdv_seq_host "$@" --Mdir "$O/$l" -o tb $F $U/test/tb_dsdv_seq_host.sv > "$O/build_$l.log" 2>&1 \
    || { echo "BUILD_FAIL $l (see $O/build_$l.log)"; return 2; }
}
bad=0
# mutant defines: 1..6 = the unit's MUT; 7 = ingest registered head stays valid after a pop (OT_ING_MUT_HREGV), 8 = engine
# realigner pointer copy 0 stalls (OT_ING_MUT_RAC) -- the APIPE 7 additions (S81-SHLK 10-18; the back-to-back refill
# mutant OT_ING_MUT_HREG needs a full-rate host stream: physical/sys_takeover/host_native_pipe_bench.py hreg7)
# 9 = the unit MUT 9: the L0 rung landing dropped (S81-SHLK2 10-18; rung one edge short)
# S81-SHLK s10 (APIPE 10, VL_EXTRA has -DOT_S81_SH_APIPE10): 11 = stream-pipe FIFO address read copy stalls
# (OT_ING_MUT_SPRH), 14 = svc decode emits on the pop edge from the previous head (OT_S81_SH_MUT_HQSTALE).
# (12 SPKIND / 13 MKD are not exercised by this bench: no partial ROWS tail, no boot marker -- SPKIND is caught by
# physical/sys_takeover/host_native_pipe_bench.py spkind10; the marker delay has no bench here, see the lane log)
mdef() { case $1 in 7) echo +define+OT_ING_MUT_HREGV;; 8) echo +define+OT_ING_MUT_RAC;; 11) echo +define+OT_ING_MUT_SPRH;;
  12) echo +define+OT_ING_MUT_SPKIND;; 13) echo +define+OT_ING_MUT_MKD;; 14) echo +define+OT_S81_SH_MUT_HQSTALE;; *) echo +define+MUT=$1;; esac; }
MUTS="1 2 3 4 5 6 7 8 9 10"; case "${VL_EXTRA:-}" in *OT_S81_SH_APIPE10*) MUTS="$MUTS 11 14";; esac
if [ "${3:-}" = base ]; then
  build base || exit 2
  for seed in $SEEDS; do
    "$O/base/tb" +seed=$seed > "$O/run_s$seed.log" 2>&1
    grep '^SEQHOST' "$O/run_s$seed.log"
    grep -q '^SEQHOST PASS' "$O/run_s$seed.log" || bad=1
  done
  exit $bad
fi
if [ -n "${3:-}" ]; then   # single-mutant mode for closure-loop benches: run_seq_host_bench.sh OUT SEED <1..9>; prints the SEQHOST lines
  m=$3; build mut$m $(mdef $m) || exit 2
  "$O/mut$m/tb" +seed=${SEEDS%% *} > "$O/run_mut$m.log" 2>&1; grep '^SEQHOST' "$O/run_mut$m.log"; exit 0
fi
build base || exit 2
for s in $SEEDS; do
  "$O/base/tb" +seed=$s > "$O/run_s$s.log" 2>&1
  grep '^SEQHOST seed' "$O/run_s$s.log"; grep -q '^SEQHOST PASS' "$O/run_s$s.log" || { echo "golden seed $s FAIL"; bad=1; }
done
for s in $SEEDS; do   # S81-SAFE-FIX/SH: two calendar rows on one edge (word-aligned and straddling pairs) through the walker
  "$O/base/tb" +seed=$s +pair=1 > "$O/run_pair_s$s.log" 2>&1
  echo "PAIR $(grep '^SEQHOST seed' "$O/run_pair_s$s.log")"; grep -q '^SEQHOST PASS' "$O/run_pair_s$s.log" || { echo "golden pair seed $s FAIL"; bad=1; }
done
"$O/base/tb" +seed=7 +collide=1 > "$O/run_collide.log" 2>&1
grep '^SEQHOST COLLIDE' "$O/run_collide.log"; grep -q 'PASS (fault raised)' "$O/run_collide.log" || { echo "collision not faulted"; bad=1; }
"$O/base/tb" +seed=3 +stdrop=1 > "$O/run_stdrop.log" 2>&1
grep '^SEQHOST STDROP' "$O/run_stdrop.log"; grep -q 'PASS (fault raised)' "$O/run_stdrop.log" || { echo "W region drop not faulted"; bad=1; }
for m in $MUTS; do
  build mut$m $(mdef $m) || { bad=1; continue; }
  "$O/mut$m/tb" +seed=1 > "$O/run_mut$m.log" 2>&1
  if grep -q '^SEQHOST PASS' "$O/run_mut$m.log"; then echo "mutant $m NOT detected"; bad=1
  else echo "mutant $m detected: $(grep -m1 '^SEQHOST seed' "$O/run_mut$m.log" | grep -o 'mism.*')"; fi
done
verilator ${VL_EXTRA:-} --lint-only -Wall -Wno-fatal --top-module dsdv_seq_host $F > "$O/lint.log" 2>&1
# waived in dsdv_seq_host.sv: DECLFILENAME (5 leaves in one file), PINCONNECTEMPTY / UNUSEDSIGNAL (the reused modules'
# diagnostic outputs the unit does not export: issuer st_*/phase/job_rdy/END pulse, vstop dl_* (seqhost taps nothing),
# ingest h_crn (static host: no receive credits, as dsfd_host_c STATIC), lane live bits), MULTIDRIVEN s_hw (dsfd_host_sd
# drives hw[0] from its reset block and the payload from a plain block)
W=$(grep '^%Warning' "$O/lint.log" | grep 'unit/dsdv_seq_host.sv' | grep -v -E 'Warning-(DECLFILENAME|PINCONNECTEMPTY|UNUSEDSIGNAL)' | grep -v -E "MULTIDRIVEN.*'s_hw(_[we])?'")
if grep -q '^%Error' "$O/lint.log" || [ -n "$W" ]; then
  echo "lint FAIL (see $O/lint.log): $W"; bad=1
else echo "lint clean: verilator -Wall, 0 errors, 0 unwaived warnings in dsdv_seq_host.sv (reused modules unchanged)"; fi
[ $bad = 0 ] && echo "SEQHOST_GATE PASS" || echo "SEQHOST_GATE FAIL"
exit $bad
