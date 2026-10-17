#!/usr/bin/env bash
# H-NETLIST/COLL-CTL 1045: issuer v5 vs original every-edge miter (Verilator 5.050).
#   run_issuer_v5_miter.sh OUT [pos|reload] [SEED] [PROGS]
# pos: exit 0 on ISSUER_V5_MITER PASS. reload: the v5 issuer with an off-by-one loop decision (MUT_RELOAD); exit
# non-zero when the miter rejects it (a loop bench with expect "fail").
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:-pos}; SEED=${3:-1}; PROGS=${4:-300}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
src=("$p/tb_hgi_coll_static_issuer_v5_miter.sv" "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_static_issuer_v5.sv"
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
sha256sum "${src[@]}" > "$OUT/sources.sha256"
D=(); [ "$MODE" = reload ] && D=(-DMUT_RELOAD)
"$V" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 --top-module tb_hgi_coll_static_issuer_v5_miter "${D[@]}" -Mdir "$OUT/obj_$MODE" "${src[@]}" > "$OUT/$MODE.build.log" 2>&1 \
 || { tail -30 "$OUT/$MODE.build.log"; exit 2; }
set +e; "$OUT/obj_$MODE/Vtb_hgi_coll_static_issuer_v5_miter" +SEED=$SEED +PROGS=$PROGS > "$OUT/$MODE.log" 2>&1; rc=$?; set -e
grep -E 'ISSUER_V5_MITER|MISMATCH' "$OUT/$MODE.log" | head -8
rm -rf "$OUT/obj_$MODE"
[ $rc = 0 ] && grep -q '^ISSUER_V5_MITER PASS' "$OUT/$MODE.log"
