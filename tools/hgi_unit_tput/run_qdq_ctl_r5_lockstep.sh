#!/bin/bash
# HBM-HUB-RTL-1 11-11 (DIE-HBM-100 ruling (B)): ot_hgi_qdq_transport_ctl_r5 (256-entry ring A) bench.
#   lockstep  ctl_r4 vs ctl_r5, same strap RLI in {2,3,11,58,100,125,126} x 3 seeds at the pass latency L = RLI, and at
#             L = RLI +-1 (both must fault on the same cycle): every output cycle for cycle
#   deep      ctl_r5 alone, RLI {126,127,128,200,254} at L = RLI: no fault, decode order / counts
#   rd1       RLI 127 (= 126 + 1, the rd1 plan event): L 127 PASS; controls L 126 (+0) and L 128 (+2) FAULT (sticky)
#   range     RLI 255 and RLI 1 -> cfg_bad fault; MUT 3 (ring A read one entry late) at RLI 127 / L 127 -> fault
# usage: run_qdq_ctl_r5_lockstep.sh OUT   (VERILATOR overrides the binary)
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1"); mkdir -p "$out"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x64_m2_r0c0_g64/ot_sram_1r1w_256x64_m2_r0c0_g64.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r4.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r5.sv
 rtl/test/hbm_accel/generic/tb_hgi_qdq_transport_ctl_r5_lockstep.sv)
"$V" --version | tee "$out/verilator.version"
for m in 0 3; do
 "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m --top-module tb_hgi_qdq_transport_ctl_r5_lockstep \
  -Mdir "$out/obj$m" -o sim "${src[@]}" > "$out/build$m.log" 2>&1 || { tail -20 "$out/build$m.log"; exit 1; }
done
res="$out/results.tsv"; printf 'case\tmut\tmode\trli\tl\tseed\texpect\tgot\tline\n' > "$res"
run() {  # case mut mode rli l seed expect(PASS|FAULT)
 local log="$out/$1_m$2_r$4_l$5_s$6.log" rc got
 set +e; "$out/obj$2/sim" +MODE=$3 +RLI=$4 +L=$5 +SEED=$6 +NCMD=${NCMD:-3000} > "$log" 2>&1; rc=$?; set -e
 if grep -q '^FAIL CTL_R5' "$log"; then got=BENCH_FAIL
 elif grep -q '^PASS CTL_R5' "$log"; then got=PASS
 elif grep -q 'FAULT_AT=[0-9]' "$log"; then got=FAULT
 else got=RC$rc; fi
 printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$got" "$(grep -m1 FAULT_AT "$log")" >> "$res"
 [[ $got == "$7" ]] || { echo "UNEXPECTED $*: $got"; tail -3 "$log"; return 1; }
}
bad=0
for r in 2 3 11 58 100 125 126; do for s in 1 2 3; do
 run lockstep 0 0 $r $r $s PASS || bad=1
done; run lockstep 0 0 $r $((r+1)) 1 FAULT || bad=1; [[ $r -gt 2 ]] && { run lockstep 0 0 $r $((r-1)) 1 FAULT || bad=1; }; done
for r in 126 127 128 200 254; do run deep 0 1 $r $r 1 PASS || bad=1; done
run rd1 0 1 127 127 2 PASS || bad=1
run rd1_ctl_plus0 0 1 127 126 1 FAULT || bad=1
run rd1_ctl_plus2 0 1 127 128 1 FAULT || bad=1
run range_255 0 1 255 255 1 FAULT || bad=1
run range_1 0 1 1 1 1 FAULT || bad=1
run mut3 3 1 127 127 1 FAULT || bad=1
rm -rf "$out"/obj0 "$out"/obj3
column -t "$res" | cut -c1-160
[[ $bad == 0 ]] && echo "ALL_EXPECTED ctl_r5" || { echo "CTL_R5_BENCH_FAIL"; exit 1; }
