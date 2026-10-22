#!/bin/bash
# lb2qc_ref4.sh (QW-REFB1 22:58) = ref3 with B0 on $D/v5050raw: the 22:45 B0 via verilator.real still hit the guard (VM_HIER_VERILATOR resolves to bin/verilator = shim).
# QW-REFB1 10-18: B1 retry.  The 19:05 B1 build was NOT 5.032: tools/exactness/qwen_rom_fulltoken.py (10-13 source too,
# since 0e82ccad6 10-07) hard-codes VERILATOR=~/.local/opentallas-tools/verilator-5.050/bin/verilator, so PATH=/usr/bin
# changed only the logged version line; the build ran the guarded 5.050 shim and failed the NBA guard (same as B2).
# The committed 10-13 receipts (results/rtl/qwen_layer_tput_1013/die_terms/*/build_receipts/verilate_die.log) show the
# 10-13 recipe WAS Verilator 5.050 with no --unroll-count (pre-guard).  Recipe fix (harness only, RTL untouched):
# srcR = srcA + a QROM_VERILATOR env hook on that constant.
#   T=B1: QROM_VERILATOR=/usr/bin/verilator (Debian 5.032), no unroll
#   T=B0: QROM_VERILATOR=verilator-5.050/bin/verilator.real (unguarded front end), no unroll = literal 10-13 recipe replay
# Each build is scanned with the 5.050 in-place-NBA signature scanner, then L0 runs (harness cycle guard, op trace).
set -u -o pipefail
D=$1; T=$2
SRC=$D/srcR; FX=/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx; LOG=$D/STATUS.log
case $T in B1) export QROM_VERILATOR=/usr/bin/verilator ;; B1u) export QROM_VERILATOR=/usr/bin/verilator ;; B0) export QROM_VERILATOR=$D/v5050raw/bin/verilator ;; *) exit 2;; esac
# B0 = unguarded 5.050: v5050raw holds copies of verilator.real + verilator_bin (same binary, cmp) so hier blocks do not re-enter the guard shim
unset QROM_VFLAGS_EXTRA VERILATOR_ROOT; UNR=0
[ $T = B1u ] && { export QROM_VFLAGS_EXTRA="--unroll-count 8192"; UNR=8192; }  # 22:45 B1 (5.032, no unroll) cannot verilate srcA: me_array_w12.sv:352 g_xq needs --unroll-count >3075
export QROM_OPTRACE=1
now() { TZ=America/Los_Angeles date '+%F %H:%M:%S'; }
log() { echo "$(now) [$T] $*" >> "$LOG"; }
cd "$SRC" || exit 2
rm -rf "$D/bld$T" "$SRC/build/qwen_missing_part/bld$T"
log "start src $(cat SOURCE_COMMIT) host $(hostname) mode L0 verilator $($QROM_VERILATOR --version | head -1) ($QROM_VERILATOR) unroll=$UNR"
t0=$(date +%s)
python3 tools/qwen_missing/partition_token.py build --variant part --build "$D/bld$T" --jobs 32 --dcu 2 --duc 2 --su-ml 7 --comp 1 > "$D/build$T.log" 2>&1; r=$?
log "build rc=$r wall_s=$(( $(date +%s) - t0 )) hier_verilator=$(grep -h VM_HIER_VERILATOR $D/bld$T/die/Vdie_hier.mk 2>/dev/null | head -1)"; [ $r = 0 ] || exit 3
python3 -I $HOME/.local/opentallas-tools/verilator-5.050/share/ot_nba_guard/verilator_nba_guard.py $(ls -d "$D/bld$T"/*/ | grep -v gen) > "$D/nbaguard$T.log" 2>&1
log "nba_guard_scan rc=$? $(grep -h -o 'INPLACE_NBA_LOOPS=[0-9]*' $D/nbaguard$T.log | tr '\n' ' ')"
t0=$(date +%s); export RT_OPTRACE=1
QWEN_FX_IMG=$FX/img_p1 QWEN_FX_GOLD=$FX/realmem/P8191 QWEN_FX_XPRE=$FX/realmem/P8191/x_preload.hex QWEN_FX_HISTORY=$FX/history_l3 \
  timeout 7200 python3 tools/qwen_missing/partition_token.py run --build "$D/bld$T" --work "$D/run$T" --stages L0 --threads 16 > "$D/run$T.log" 2>&1; r=$?
log "runL0 rc=$r wall_s=$(( $(date +%s) - t0 )) $(tail -1 "$D/run$T.log" | head -c 300)"
exit $r
