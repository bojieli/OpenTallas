#!/usr/bin/env bash
# HBM-COLLQ3-V7 10-19: 128-row issuer core v7_r128 vs v6 #(ROWS 128) AND leaf issuer_m128v7 vs issuer_m #(ROWS 128)
# every-edge miter (Verilator 5.050). One bench per MODE.
#   run_issuer_v7r128_miter.sh OUT [pos|reload|nofwd|swap] [SEED] [PROGS]
# pos: exit 0 on ISSUER_V7R128_MITER PASS. Mutants (job benches with expect fail: exit 1 printing
# 'ISSUER_V7R128_MUTANT_REJECTED <mode>' when the miter rejects the mutant; exit 0 + SURVIVED otherwise): reload = v7 loop decision off by one (MUT_RELOAD), nofwd = no counter forwarding
# when the successor shares the visited row's loop id, swap = grand-successor pairs swapped in the lookahead.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:-pos}; SEED=${3:-1}; PROGS=${4:-300}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
p=$ROOT/rtl/hbm_accel/generic/collective/p2p; M=$ROOT/physical/asap7_memory_macros
src=("$p/tb_hgi_coll_static_issuer_v7r128_miter.sv" "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_static_issuer_v6.sv"
 "$p/ot_hgi_coll_static_issuer_v7r128.sv" "$p/ot_hfd_coll_q_hard_v5.sv" "$M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$M/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v"
 "$M/ot_sram_1rw_128x64_m2_r2c2_p192_mir/ot_sram_1rw_128x64_m2_r2c2_p192_mir.v")
sha256sum "${src[@]}" "$0" > "$OUT/sources.sha256"; "$V" --version > "$OUT/verilator.version"
D=()
case $MODE in pos) ;; reload) D=(-DMUT_RELOAD +define+OT_COLL_ISS7_MUT_RELOAD);; nofwd) D=(+define+OT_COLL_ISS7_MUT_NOFWD);; swap) D=(+define+OT_COLL_ISS7_MUT_SWAP);;
 *) echo "unknown mode $MODE"; exit 2;; esac
"$V" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTITOP -Wno-MODMISSING \
 --top-module tb_hgi_coll_static_issuer_v7r128_miter "${D[@]}" -Mdir "$OUT/obj_$MODE" "${src[@]}" > "$OUT/$MODE.build.log" 2>&1 \
 || { tail -30 "$OUT/$MODE.build.log"; echo "ISSUER_V7R128_MITER build FAIL"; exit 2; }
set +e; "$OUT/obj_$MODE/Vtb_hgi_coll_static_issuer_v7r128_miter" +SEED=$SEED +PROGS=$PROGS > "$OUT/$MODE.log" 2>&1; rc=$?; set -e
grep -E 'ISSUER_V7R128_MITER|MISMATCH' "$OUT/$MODE.log" | head -8
rm -rf "$OUT/obj_$MODE"
if [ "$MODE" = pos ]; then [ $rc = 0 ] && grep -q '^ISSUER_V7R128_MITER PASS' "$OUT/$MODE.log"; exit $?; fi
if [ $rc != 0 ] && grep -q '^ISSUER_V7R128_MITER FAIL' "$OUT/$MODE.log"; then echo "ISSUER_V7R128_MUTANT_REJECTED $MODE"; exit 1; fi
echo "ISSUER_V7R128_MUTANT_SURVIVED $MODE"; exit 0
