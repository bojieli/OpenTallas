#!/bin/bash
# LB2-QWEN-C / Q-LBGAP2 10-18 bisect step 2: A (10-13 source 30b6440b5) ALSO hangs at op prog_a=20 (cyc 3094, same trace as
# the 10-18 source C) -> RTL drift is not the cause.  Remaining variables vs the 10-13 run: Verilator version (10-13 = system
# 5.032, 10-18 = 5.050) and the 10-18 --unroll-count 4096 flag.  lb2qc_ref2.sh D T VER UNROLL  (L0 mode, harness cycle guard, op trace)
#   T=B1: srcA, Verilator 5.032 (system), no unroll flag  = the 10-13 recipe  -> must retire L0 at 6,151 exact (else fixtures)
#   T=B2: srcA, Verilator 5.050, no unroll flag           -> separates Verilator version from the unroll flag
set -u -o pipefail
D=$1; T=$2; VER=$3; UNROLL=$4
SRC=$D/srcA; FX=/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx; LOG=$D/STATUS.log
[ "$VER" = 5050 ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
[ "$UNROLL" = 1 ] && export QROM_VFLAGS_EXTRA="--unroll-count 4096"
export QROM_OPTRACE=1
now() { TZ=America/Los_Angeles date '+%F %H:%M:%S'; }
log() { echo "$(now) [$T] $*" >> "$LOG"; }
cd "$SRC" || exit 2
log "start src $(cat SOURCE_COMMIT) host $(hostname) mode L0 verilator $(verilator --version | head -1) unroll=$UNROLL"
t0=$(date +%s)
python3 tools/qwen_missing/partition_token.py build --variant part --build "$D/bld$T" --jobs 32 --dcu 2 --duc 2 --su-ml 7 --comp 1 > "$D/build$T.log" 2>&1; r=$?
log "build rc=$r wall_s=$(( $(date +%s) - t0 ))"; [ $r = 0 ] || exit 3
t0=$(date +%s); export RT_OPTRACE=1
QWEN_FX_IMG=$FX/img_p1 QWEN_FX_GOLD=$FX/realmem/P8191 QWEN_FX_XPRE=$FX/realmem/P8191/x_preload.hex QWEN_FX_HISTORY=$FX/history_l3 \
  timeout 7200 python3 tools/qwen_missing/partition_token.py run --build "$D/bld$T" --work "$D/run$T" --stages L0 --threads 16 > "$D/run$T.log" 2>&1; r=$?
log "runL0 rc=$r wall_s=$(( $(date +%s) - t0 )) $(tail -1 "$D/run$T.log" | head -c 300)"
exit $r
