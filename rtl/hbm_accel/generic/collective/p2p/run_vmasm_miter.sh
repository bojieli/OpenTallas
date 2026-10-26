#!/usr/bin/env bash
# V6 VM-assembly leaf miter (Icarus).  run_vmasm_miter.sh OUT [pos|vmsel] [N]
# pos: exit 0 on VMASM_MITER PASS. vmsel: the half-swap mutant; exit non-zero when the miter rejects it (expect "fail").
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:-pos}; N=${3:-4000}; mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
D=(); [ "$MODE" = vmsel ] && D=(-DOT_COLL_V6_MUT_VMSEL)
iverilog -g2012 "${D[@]}" -o "$OUT/vmasm_$MODE.vvp" "$p/tb_hgi_coll_vmasm_miter.sv" "$p/ot_hgi_coll_ctl_v5.sv" > "$OUT/build_$MODE.log" 2>&1 || { tail -20 "$OUT/build_$MODE.log"; exit 2; }
set +e; vvp "$OUT/vmasm_$MODE.vvp" +N=$N > "$OUT/$MODE.log" 2>&1; rc=$?; set -e
grep -E 'VMASM_MITER|MISMATCH' "$OUT/$MODE.log" | head -5
[ $rc = 0 ] && grep -q '^VMASM_MITER PASS' "$OUT/$MODE.log"
