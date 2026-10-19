#!/usr/bin/env bash
# MU-S81/HOST benches on Verilator 5.050 (the closure daemon's version): dsdv_mu_hslot (host-plane slot table) and
# dsdv_mu_seed (per-MTP-user seed-state addressing).  For each: multi-user exact runs, user 0 trace identical to the
# single-user run, the collision run must fault, mutants 1 (user field dropped) and 2 (collision check dropped) must
# FAIL; plus verilator -Wall lint of both leaves and of the dsdv_seq_host_mu wrapper on the real dsdv_seq_host sources.
# Usage: run_mu_host_bench.sh OUTDIR      Prints MU_HOST_GATE PASS/FAIL.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:-$(mktemp -d)}"); mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | tee "$O/verilator_version.txt"
U=$R/rtl/dsrom_sys/s81_dv/unit
bad=0
build() { n=$1; top=$2; shift 2
  verilator --binary --timing -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module $top "$@" \
    --Mdir "$O/obj_$n" -o tb > "$O/build_$n.log" 2>&1 || { echo "BUILD_FAIL $n"; tail -20 "$O/build_$n.log"; return 2; }
}
run() { n=$1; "$O/obj_$n/tb" > "$O/run_$n.log" 2>&1; grep -E '^(MUHSLOT|MUSEED|ERR)' "$O/run_$n.log" | head -8 | sed "s/^/[$n] /"; }
HS="$R/rtl/lib/ot_rst_relay.sv $U/dsdv_mu_hslot.sv $U/test/tb_dsdv_mu_hslot.sv"
SD="$R/rtl/lib/ot_rst_relay.sv $U/dsdv_mu_seed.sv $U/test/tb_dsdv_mu_seed.sv"
# ---- (a) host slot table: NS 8 / NS 47 (47 outstanding) vs the single-user NS 1 of the same round
for cfg in "hs8 8 8" "hs47 47 47" "hs1p8 1 8" "hs1p47 1 47"; do set -- $cfg
  build $1 tb_dsdv_mu_hslot +define+NS=$2 +define+NP=$3 $HS && run $1
done
for p in 8 47; do
  grep -q '^MUHSLOT PASS' "$O/run_hs$p.log" || { echo "hslot NS $p FAIL"; bad=1; }
  grep -q '^MUHSLOT PASS' "$O/run_hs1p$p.log" || { echo "hslot single (round $p) FAIL"; bad=1; }
  if diff <(grep '^U0 ' "$O/run_hs1p$p.log") <(grep '^U0 ' "$O/run_hs$p.log") > "$O/u0_diff_hs$p.txt"; then
    echo "hslot NS $p: user 0 trace identical to single-user ($(grep -c '^U0 ' "$O/run_hs$p.log") events)"
  else echo "hslot NS $p: user 0 trace DIFFERS (see u0_diff_hs$p.txt)"; bad=1; fi
done
build hs8c tb_dsdv_mu_hslot +define+NS=8 +define+NP=8 +define+COLLIDE=1 $HS && run hs8c
grep -q 'PASS (fault raised)' "$O/run_hs8c.log" || { echo "hslot collision not faulted"; bad=1; }
build hs8o tb_dsdv_mu_hslot +define+NS=8 +define+NP=8 +define+OFFCAL=1 $HS && run hs8o
grep -q 'PASS (fault raised)' "$O/run_hs8o.log" || { echo "hslot off-calendar start not faulted"; bad=1; }
for m in 1 2; do
  build hs8m$m tb_dsdv_mu_hslot +define+NS=8 +define+NP=8 +define+MUT=$m $HS && run hs8m$m
  build hs8m${m}c tb_dsdv_mu_hslot +define+NS=8 +define+NP=8 +define+MUT=$m +define+COLLIDE=1 $HS && run hs8m${m}c
  if grep -q '^MUHSLOT PASS' "$O/run_hs8m$m.log" && grep -q 'PASS (fault raised)' "$O/run_hs8m${m}c.log"; then
    echo "hslot mutant $m NOT detected"; bad=1
  else echo "hslot mutant $m detected (FAIL as required)"; fi
done
# ---- (b) seed-state addressing: NU 4 / NU 10 vs single-user NU 1 of the same round
for cfg in "sd4 4 4" "sd10 10 10" "sd1p4 1 4" "sd1p10 1 10"; do set -- $cfg
  build $1 tb_dsdv_mu_seed +define+NU=$2 +define+NUP=$3 $SD && run $1
done
for p in 4 10; do
  grep -q '^MUSEED PASS' "$O/run_sd$p.log" || { echo "seed NU $p FAIL"; bad=1; }
  grep -q '^MUSEED PASS' "$O/run_sd1p$p.log" || { echo "seed single (round $p) FAIL"; bad=1; }
  if diff <(grep '^U0 ' "$O/run_sd1p$p.log") <(grep '^U0 ' "$O/run_sd$p.log") > "$O/u0_diff_sd$p.txt"; then
    echo "seed NU $p: user 0 trace identical to single-user ($(grep '^U0 ' "$O/run_sd$p.log"))"
  else echo "seed NU $p: user 0 trace DIFFERS"; bad=1; fi
done
build sd4c tb_dsdv_mu_seed +define+NU=4 +define+COLLIDE=1 $SD && run sd4c
grep -q 'PASS (fault raised)' "$O/run_sd4c.log" || { echo "seed collision not faulted"; bad=1; }
for m in 1 2; do
  build sd4m$m tb_dsdv_mu_seed +define+NU=4 +define+MUT=$m $SD && run sd4m$m
  build sd4m${m}c tb_dsdv_mu_seed +define+NU=4 +define+MUT=$m +define+COLLIDE=1 $SD && run sd4m${m}c
  if grep -q '^MUSEED PASS' "$O/run_sd4m$m.log" && grep -q 'PASS (fault raised)' "$O/run_sd4m${m}c.log"; then
    echo "seed mutant $m NOT detected"; bad=1
  else echo "seed mutant $m detected (FAIL as required)"; fi
done
# ---- lint: both leaves, and the wrapper on the real unit sources (NSLOT 47 and NSLOT 1)
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $U/dsdv_mu_hslot.sv"
for t in "dsdv_mu_hslot -GNSLOT=47 $R/rtl/lib/ot_rst_relay.sv $U/dsdv_mu_hslot.sv" \
         "dsdv_mu_seed -GNUSER=10 $R/rtl/lib/ot_rst_relay.sv $U/dsdv_mu_seed.sv" \
         "dsdv_seq_host_mu -GNSLOT=47 $F" "dsdv_seq_host_mu -GNSLOT=1 $F"; do set -- $t; top=$1; g=$2; shift 2
  verilator --lint-only -Wall -Wno-fatal --top-module $top $g "$@" > "$O/lint_${top}_${g#-G}.log" 2>&1
  W=$(grep -E '^%(Warning|Error)' "$O/lint_${top}_${g#-G}.log" | grep -E 'dsdv_mu_(hslot|seed)\.sv' | grep -v -E 'Warning-(DECLFILENAME|UNUSEDSIGNAL)')
  if grep -q '^%Error' "$O/lint_${top}_${g#-G}.log" || [ -n "$W" ]; then echo "lint $top $g FAIL: $W"; grep '^%Error' "$O/lint_${top}_${g#-G}.log" | head -5; bad=1
  else echo "lint $top $g clean (verilator -Wall: 0 errors, 0 unwaived warnings in the new files)"; fi
done
[ $bad = 0 ] && echo "MU_HOST_GATE PASS" || echo "MU_HOST_GATE FAIL"
exit $bad
