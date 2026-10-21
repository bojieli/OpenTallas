#!/usr/bin/env bash
set -euo pipefail
SRC_RUN=/srv/opentallas-scratch/claude/closure-loop/dsdv_sh_lk_s10gq-dsdv_sh_lk_s10gq-e316c4132
OUT=/srv/opentallas-scratch/claude/codex-s81-shlk-benchfix-1021
mkdir -p "$OUT"
BASE="$SRC_RUN/seqhost_exact/base/tb"
sha256sum "$BASE" "$SRC_RUN/bench_src_a1/rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_bench.sh" > "$OUT/sources.sha256"
for s in 1 2; do
 "$BASE" +seed=$s > "$OUT/run_s$s.log" 2>&1
 grep -q '^SEQHOST PASS' "$OUT/run_s$s.log"
 "$BASE" +seed=$s +pair=1 > "$OUT/run_pair_s$s.log" 2>&1
 grep -q '^SEQHOST PASS' "$OUT/run_pair_s$s.log"
done
"$BASE" +seed=7 +collide=1 > "$OUT/run_collide.log" 2>&1
grep -q 'PASS (fault raised)' "$OUT/run_collide.log"
"$BASE" +seed=3 +stdrop=1 > "$OUT/run_stdrop.log" 2>&1
grep -q 'PASS (fault raised)' "$OUT/run_stdrop.log"
for p in "$OUT"/run*.log; do grep '^SEQHOST' "$p"; done
printf '%s\n' 'SEQHOST_GATE PASS source=e316c4132 base+pair+collision+region-drop; actual unit/N32 causal mutants remain separate mandatory stages'
