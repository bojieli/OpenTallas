#!/usr/bin/env bash
# F20 relay tree unit bench (Icarus).  run_f20_relay.sh OUT [pos|mut1|mut2] [N]
# pos: exit 0 on F20_RELAY_TREE PASS; mutN: that mutant in one level-2 node, exit non-zero when rejected (expect "fail").
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:-pos}; N=${3:-3000}; mkdir -p "$OUT"
D=(); case "$MODE" in mut1) D=(-DMUTSEL=1);; mut2) D=(-DMUTSEL=2);; pos) ;; *) echo "mode?"; exit 2;; esac
iverilog -g2012 "${D[@]}" -o "$OUT/t_$MODE.vvp" "$HERE/tb_hgi_f20_relay4.sv" "$HERE/ot_hgi_f20_relay4.sv" > "$OUT/build_$MODE.log" 2>&1 || { tail -20 "$OUT/build_$MODE.log"; exit 2; }
set +e; vvp "$OUT/t_$MODE.vvp" +N=$N > "$OUT/$MODE.log" 2>&1; rc=$?; set -e
grep -E 'F20_RELAY_TREE|MISMATCH' "$OUT/$MODE.log" | head -5
[ $rc = 0 ] && grep -q '^F20_RELAY_TREE PASS' "$OUT/$MODE.log"
