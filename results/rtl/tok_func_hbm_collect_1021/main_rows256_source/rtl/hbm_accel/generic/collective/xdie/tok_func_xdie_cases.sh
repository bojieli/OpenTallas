#!/usr/bin/env bash
# tok_func_xdie_cases.sh <assembled src> <out dir> <variant>   (TOK-FUNC-HBM-XDIE 2026-10-21; called by tok_func_xdie.sh)
# Builds the two-die XDIE step vehicle from <src>/xdie_flist.txt + <src>/xdie_defines.txt (Verilator 5.050) and runs the
# token-pass collective cases of <variant> with the staging of run_xdie_hbm_step{,4,5,6}.sh:
#   single block (P <= 64): A probe -> B (release READY+80) -> pass (READY+8, MUST PASS)
#   multi block  (P > 64) : A -> B (guard 8) -> pass (guard 8); B and pass MUST PASS (step5/6 rule)
# A compiler refusal (programme does not fit the issuer rows / no iterated tags) is recorded as CASE ... FAIL compile.
# r14_coll_ar runs the existing AR-step vehicle (run_xdie_hbm_coll.sh ds + qw) on the same source.
set -u
SRC=$(realpath "$1"); OUT=$(realpath -m "$2"); VAR=$3; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
"$V" --version | tee "$OUT/verilator.version"
X=$SRC/rtl/hbm_accel/generic/collective/xdie
if [ "$VAR" = r14_coll_ar ]; then
  rc=0
  for c in ds qw; do bash "$X/run_xdie_hbm_coll.sh" "$SRC" "$OUT/coll_$c" $c > "$OUT/coll_$c.client.log" 2>&1 || rc=1; done
  for c in ds qw; do
    if grep -q '^XDIE2 .* PASS$' "$OUT/coll_$c/${c}_pass.log" 2>/dev/null; then echo "CASE ar_step_$c PASS"; else echo "CASE ar_step_$c FAIL"; fi
  done | tee "$OUT/cases.txt"
  echo "TOKFUNC_XDIE_DONE $VAR rc=$rc" | tee -a "$OUT/cases.txt"; exit $rc
fi
C="python3 $SRC/tools/xdie_hbm_step_compile.py"
F=$(sed "s#^#$SRC/#" "$SRC/xdie_flist.txt" | tr '\n' ' ')
DEFS=$(cat "$SRC/xdie_defines.txt")
(cd "$SRC" && sha256sum $(cat xdie_flist.txt) rtl/hbm_accel/generic/collective/xdie/tb_xdie_hbm_step.sv tools/xdie_hbm_step_compile.py \
  rtl/hbm_accel/generic/collective/p2p/static_uop_layout_v4.json) > "$OUT/sources.sha256"
echo "$DEFS" > "$OUT/defines.txt"
"$V" --binary --timing -O1 -j ${JOBS:-16} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-MULTITOP -Wno-BLKSEQ -Wno-WIDTHCONCAT +incdir+$SRC/rtl/dsrom_sys/s81_link \
  -I$SRC --top-module tb_xdie_hbm_step $DEFS --Mdir "$OUT/obj" -o tb $X/tb_xdie_hbm_step.sv $F > "$OUT/build.log" 2>&1 \
  || { tail -60 "$OUT/build.log"; echo "CASE build FAIL" | tee "$OUT/cases.txt"; echo "TOKFUNC_XDIE_DONE $VAR rc=2" | tee -a "$OUT/cases.txt"; exit 2; }
echo "TOKFUNC build ok"
ROWS=$(grep -o 'XDIE_ROWS=[0-9]*' <<< "$DEFS" | cut -d= -f2); AR=$(grep -o 'XDIE_AR_ITER=[0-9]*' <<< "$DEFS" | cut -d= -f2)
if [ "$AR" = 1 ]; then AI="--ar-iter --rows $ROWS --del-edge 1"; ADR=+ADRCHK; else AI=""; ADR=""; fi
stage() {  # tag swd xargs compile-args...
  local tag=$1 swd=$2 xa=$3 args; shift 3
  $C "$OUT/$tag" --swd "$swd" "$@" > "$OUT/$tag.compile.log" 2>&1 || { tail -3 "$OUT/$tag.compile.log"; echo "STAGE $tag COMPILE_FAIL"; return 3; }
  cp "$OUT/$tag.compile.log" "$OUT/$tag/compile.log"
  args=$(grep -o '^XDIE2_ARGS .*' "$OUT/$tag.compile.log" | cut -d' ' -f2-)
  { cat "$OUT/$tag.compile.log"; timeout 7200 "$OUT/obj/tb" +verilator+seed+7 +DIR="$OUT/$tag" +SWD=$swd $ADR $xa $args; } > "$OUT/$tag.log" 2>&1
  grep -E '^XDIE2 |XDIE3_(STEP|E)|XDIE2_(FAULT|SCHED_FAIL|ERR)' "$OUT/$tag.log" | head -6
  rm -rf "$OUT/$tag"/*.hex 2>/dev/null; return 0
}
case_run() {  # name swd kind frames
  local n=$1 swd=$2 k=$3 p=$4 xa="" g=80
  [ "$k$p" = rs144 ] && xa=+T0=15807          # same TX gearbox launch phase as XDIE-HBM5 (run_xdie_hbm_step6.sh)
  [ "$p" -gt 64 ] && g=8
  stage ${n}_A $swd "$xa" --kind $k --frames $p --from - $AI || { echo "CASE $n FAIL compile $(grep -m1 -iE 'assert|error|exceed|fit' "$OUT/${n}_A.compile.log" | cut -c1-200)"; return; }
  stage ${n}_B $swd "$xa" --kind $k --frames $p --from "$OUT/${n}_A.log" --guard $g $AI || { echo "CASE $n FAIL compile_B"; return; }
  stage ${n}_pass $swd "$xa" --kind $k --frames $p --from "$OUT/${n}_B.log" --guard 8 $AI || { echo "CASE $n FAIL compile_pass"; return; }
  if grep -q '^XDIE2 .* PASS$' "$OUT/${n}_pass.log" && { [ "$p" -le 64 ] || grep -q '^XDIE2 .* PASS$' "$OUT/${n}_B.log"; }; then
    echo "CASE $n PASS $(grep -m1 '^XDIE3_E' "$OUT/${n}_pass.log")"
  else echo "CASE $n FAIL sim $(grep -m1 -E '^XDIE2 ' "$OUT/${n}_pass.log")"; fi
}
CASES="qw_ag64:4:ag:64 qw_ag32:4:ag:32 qw_ag16:4:ag:16 qw_rs64:4:rs:64 qw_rs32:4:rs:32 qw_rs16:4:rs:16
 ds_ag48:333:ag:48 ds_ag144:333:ag:144 ds_rs48:333:rs:48 ds_rs144:333:rs:144"
[ "$VAR" = main_rows256 ] && CASES="ds_ag48:333:ag:48 ds_ag144:333:ag:144 ds_rs144:333:rs:144"
: > "$OUT/cases.txt"
for c in $CASES; do IFS=: read -r n s k p <<< "$c"; case_run $n $s $k $p | tee -a "$OUT/cases.txt"; done
rm -rf "$OUT/obj"
grep -q 'CASE .* FAIL' "$OUT/cases.txt" && rc=1 || rc=0
echo "TOKFUNC_XDIE_DONE $VAR rc=$rc" | tee -a "$OUT/cases.txt"
exit $rc
