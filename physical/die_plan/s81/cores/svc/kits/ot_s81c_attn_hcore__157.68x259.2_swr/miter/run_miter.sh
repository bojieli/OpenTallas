#!/bin/bash
# PATH-S81/HCORE miter runner: $1 = f12|hcore, $2 = pass|mut, $3 = seeds (e.g. "1 2 3"), $4 = cycles
# REF = unchanged EH kit rtl (renamed *_ref), NEW = rtl with the OT_F12_SWAP_REP change.  Exit 0 only if every seed PASSes
# (pass mode) or every seed FAILs with mismatches (mut mode).
set -uo pipefail
T=$1; M=$2; SEEDS=$3; CYC=$4
B=$(cd "$(dirname "$0")" && pwd)
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
W=$B/build_${T}_${M}; rm -rf "$W"; mkdir -p "$W/ref"
mods=$(grep -h -o -E '^\s*module\s+[A-Za-z0-9_]+' $B/ref_rtl/*.sv | awk '{print $2}' | sort -u)
for f in $B/ref_rtl/*.sv; do
  cp "$f" "$W/ref/$(basename "$f" .sv)_ref.sv"
  for m in $mods; do sed -i -E "s/\\b${m}\\b/${m}_ref/g" "$W/ref/$(basename "$f" .sv)_ref.sv"; done
done
DEFS="+define+SYNTHESIS +define+OT_S81C_HCORE_CTLA +define+OT_S81C_HCORE_RSTE +define+OT_F12_SWAP_REP"
[ "$M" = mut ] && DEFS="$DEFS +define+OT_F12_SWAP_REP_MUT"
if [ "$T" = f12 ]; then
  SRC="$B/new_rtl/ot_hdc_fp32_f12.sv $B/new_rtl/ot_hdc_prefix.sv $B/new_rtl/ot_hdc_fastfp.sv $W/ref/ot_hdc_fp32_f12_ref.sv $W/ref/ot_hdc_prefix_ref.sv $W/ref/ot_hdc_fastfp_ref.sv $B/tb_f12_swr.sv"
else
  SRC="$(ls $B/new_rtl/*.sv) $(ls $W/ref/*.sv) $B/tb_hcore_swr.sv"
fi
echo "PATH_S81_HCORE_MITER build $T $M defs: $DEFS"
sha256sum $B/new_rtl/*.sv $B/ref_rtl/*.sv $B/tb_*.sv
$V --binary -O3 --top-module tb -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC --x-assign 0 --x-initial 0 \
   -j 16 --Mdir "$W/obj" $DEFS $SRC > "$W/build.log" 2>&1 || { tail -30 "$W/build.log"; echo "PATH_S81_HCORE_MITER BUILD_FAIL $T $M"; exit 2; }
rc=0
for s in $SEEDS; do
  out=$("$W/obj/Vtb" +seed=$s +cycles=$CYC 2>&1 | grep -E "MITER|MISMATCH" | tail -6); echo "$out"
  line=$(echo "$out" | grep MITER)
  if [ "$M" = pass ]; then echo "$line" | grep -q " PASS " || rc=1
  else echo "$line" | grep -q -E "mismatches=[1-9]" || rc=1; fi
done
echo "PATH_S81_HCORE_MITER DONE $T $M rc=$rc ($([ $M = pass ] && echo 'all seeds PASS' || echo 'mutant CAUGHT on every seed') iff rc=0)"
exit $rc
