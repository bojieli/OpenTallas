#!/usr/bin/env bash
set -uo pipefail
TASK=/srv/opentallas-scratch/claude/codex-hbm-token-0936-1023
SOURCE=/srv/opentallas-scratch/claude/tokd-hbm2/r18h5_src
NAME=${1:?corrected_rec2 or negative_omit_bccw}
case "$NAME" in corrected_rec2|negative_omit_bccw) ;; *) exit 2 ;; esac
BIN=$SOURCE/out/obj/Vtb_hbm_slice
EXPECTED=273a0824d5a41776fad17c2c0ddb990a3fb8dd41c797381edd28fe81644d87e0
ACTUAL=$(sha256sum "$BIN" | awk '{print $1}')
[ "$ACTUAL" = "$EXPECTED" ] || exit 3
R=$TASK/$NAME
O=$TASK/validation_$NAME
[ ! -e "$O/run.log" ] || exit 4
mkdir -p "$O"
printf '%s\n' "REC2 COMPONENT ONLY; $NAME; not a native layer, chain, token or physical-clock qualification." > "$O/scope.txt"
/usr/bin/time -v -o "$O/run.time" "$BIN" +verilator+rand+reset+0 +REPLAY="$R" +CYCLES=450 +SHOWVAL > "$O/run.log" 2>&1
simrc=$?
python3 "$SOURCE/check_slice_run.py" --replay "$R" --run-log "$O/run.log" --boundary "$SOURCE/slice/boundary.json" --tb-source "$SOURCE/slice/tb_slice.sv" --out "$O/acceptance.json" > "$O/check.log" 2>&1
checkrc=$?
printf 'SIM_RC=%s CHECK_RC=%s\n' "$simrc" "$checkrc" > "$O/exit.txt"
[ "$simrc" = 0 ] || exit "$simrc"
exit "$checkrc"
