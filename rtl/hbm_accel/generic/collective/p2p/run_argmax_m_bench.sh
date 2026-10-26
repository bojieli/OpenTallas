#!/usr/bin/env bash
# run_argmax_m_bench.sh OUT [pos|late]: argmax_m_tp192 (START_REG=1) on the compiled ARGMAX stimulus; late = start +2 mutant (must FAIL)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);OUT=$(realpath -m "${1:?out}");MODE=${2:-pos};mkdir -p "$OUT";cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p;D=();[ "$MODE" = late ] && D=(-DOT_ARGMAX_MUT_START_LATE)
src=("$P/tb_hgi_coll_argmax_m.sv" "$P/ot_hfd_coll_q_hard_v5.sv" "$P/ot_hgi_coll_argmax_static.sv" rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv)
sha256sum "${src[@]}" "$0" > "$OUT/sources.sha256"
"$V" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MODMISSING "${D[@]}" --top-module tb_hgi_coll_argmax_m -Mdir "$OUT/obj" "${src[@]}" > "$OUT/build.log" 2>&1 || { tail -20 "$OUT/build.log"; exit 2; }
set +e; "$OUT/obj/Vtb_hgi_coll_argmax_m" > "$OUT/run.log" 2>&1; rc=$?; set -e
cat "$OUT/run.log"; exit $rc
