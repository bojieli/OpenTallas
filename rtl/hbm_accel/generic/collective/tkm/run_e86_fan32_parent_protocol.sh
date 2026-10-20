#!/usr/bin/env bash
set -euo pipefail
C=rtl/hbm_accel/generic/collective/tkm
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p out
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_sim/e86_parent_protocol_vectors_1020.py --out out/vec > out/vectors.log
sha256sum "$C/ot_hgi_coll_tkm.sv" "$C/ot_hgi_coll_tkm_static.sv" "$C/ot_hgi_coll_tkm_buffer.sv" "$C/tb_hgi_coll_tkm_static_fan32_protocol.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v tools/hgi_sim/e86_parent_protocol_vectors_1020.py tools/hgi_coll_tkm_vectors.py > out/sources.sha256
"$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hgi_coll_tkm_static_fan32_protocol -Mdir out/obj "$C/tb_hgi_coll_tkm_static_fan32_protocol.sv" "$C/ot_hgi_coll_tkm_static.sv" "$C/ot_hgi_coll_tkm.sv" "$C/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > out/build.log 2>&1
for seed in 17 1020; do
 for tc in full192_random group4_long rank128_zero64; do
  out/obj/Vtb_hgi_coll_tkm_static_fan32_protocol +DIR=out/vec/$tc +verilator+rand+reset+2 +verilator+seed+$seed > out/${tc}_seed${seed}.log 2>&1
  grep 'TKM_STATIC PASS' out/${tc}_seed${seed}.log
 done
done
for mut in 1 2; do
 set +e
 out/obj/Vtb_hgi_coll_tkm_static_fan32_protocol +DIR=out/vec/full192_random +PROTOCOL_MUT=$mut +verilator+rand+reset+2 +verilator+seed+1020 > out/protocol_mut${mut}.log 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q 'MISMATCH [OR]' out/protocol_mut${mut}.log || ! grep -q 'TKM_STATIC FAIL' out/protocol_mut${mut}.log; then
  echo "PROTOCOL_MUTANT_NOT_CAUSAL $mut rc=$rc";exit 8
 fi
 echo "PROTOCOL_MUTANT_CAUSAL $mut rc=$rc"
done
echo E86_PARENT_PROTOCOL_ALL_PASS
