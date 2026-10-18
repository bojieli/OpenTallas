#!/bin/bash
# LB2-QWEN-C 10-18: reference-core regression bisect for the 10-13 per-layer numbers.
#   lb2qc_ref.sh D T MODE   T=A: 10-13 source 30b6440b5 (+ the 10-18 harness env hooks only), unrolled build, restored fixtures
#                           T=C: rebuild source 8a01e4a5 with the observation-only op-fetch trace (QROM_OPTRACE / RT_OPTRACE)
set -u -o pipefail
D=$1; T=$2; MODE=$3
SRC=$D/src$T; FX=/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx; LOG=$D/STATUS.log
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export QROM_VFLAGS_EXTRA="--unroll-count 4096"
[ "$T" = C ] && export QROM_OPTRACE=1
now() { TZ=America/Los_Angeles date '+%F %H:%M:%S'; }
log() { echo "$(now) [$T] $*" >> "$LOG"; }
cd "$SRC" || exit 2
log "start src $(cat SOURCE_COMMIT) host $(hostname) mode $MODE"
t0=$(date +%s)
python3 tools/qwen_missing/partition_token.py build --variant part --build "$D/bld$T" --jobs 32 --dcu 2 --duc 2 --su-ml 7 --comp 1 > "$D/build$T.log" 2>&1; r=$?
log "build rc=$r wall_s=$(( $(date +%s) - t0 ))"; [ $r = 0 ] || exit 3
t0=$(date +%s)
[ "$T" = C ] && export RT_OPTRACE=1
QWEN_FX_IMG=$FX/img_p1 QWEN_FX_GOLD=$FX/realmem/P8191 QWEN_FX_XPRE=$FX/realmem/P8191/x_preload.hex QWEN_FX_HISTORY=$FX/history_l3 \
  python3 tools/qwen_missing/partition_token.py run --build "$D/bld$T" --work "$D/run$T" --stages $MODE --threads 16 > "$D/run$T.log" 2>&1; r=$?
log "run$MODE rc=$r wall_s=$(( $(date +%s) - t0 )) $(tail -1 "$D/run$T.log" | head -c 300)"
exit $r
