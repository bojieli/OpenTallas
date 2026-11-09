#!/bin/bash
# re-runnable: builds the bench twice (real form, swapped-half mutant); PASS = real PASS and mutant FAIL
set -u
cd "$(dirname "$0")"
# inputs (copied next to this script by the caller): ot_wbq_split.sv, ot_hbm_accel_cdc_fifo.sv, ot_reset_sync.sv and the
# behavioural views ot_sram_1r1w_128x256_m1_r0c0_g256.v / ot_sram_1r1w_128x128_m1_r0c0_g128.v; the mutant swaps the two
# rd_out halves of ot_wbq_root_payload_ps
python3 -I - <<'PY'
t=open('ot_wbq_split.sv').read()
a='.rd_out(rd_out[127:0])';b='.rd_out(rd_out[255:128])'
assert t.count(a)==1 and t.count(b)==1
open('ot_wbq_split_mut.sv','w').write(t.replace(a,'@@A').replace(b,a).replace('@@A',b))
PY
V=$HOME/.local/opentallas-tools/bin/verilator
for m in real mut; do
 f=ot_wbq_split.sv; [ $m = mut ] && f=ot_wbq_split_mut.sv
 rm -rf obj_$m; $V --binary -j 4 -Wno-fatal -Wno-lint --top-module tb -Mdir obj_$m -o sim tb_g1ps.sv $f ot_hbm_accel_cdc_fifo.sv ot_reset_sync.sv ot_sram_1r1w_128x256_m1_r0c0_g256.v ot_sram_1r1w_128x128_m1_r0c0_g128.v > build_$m.log 2>&1 || { echo "BUILD_FAIL $m"; tail -20 build_$m.log; exit 2; }
 ./obj_$m/sim > sim_$m.log 2>&1; tail -2 sim_$m.log
done
if grep -q '^PASS' sim_real.log && grep -q '^FAIL' sim_mut.log; then echo PROOF_PASS | tee result.txt; else echo PROOF_FAIL | tee result.txt; exit 1; fi
