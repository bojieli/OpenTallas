#!/usr/bin/env bash
# S-NET: ot_s81_static_ratio_cross exact over every divider phase and marker release (4:3 and 3:4), skipped-phase fault,
# and the mapping mutant.   run_ratio_static_gate.sh pass|mut OUT
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?}; out=${2:?}; mkdir -p "$out"
src=(rtl/dsrom_sys/s81_static_net/ot_s81_static_ratio_cross.sv rtl/dsrom_sys/s81_static_net/test/tb_s81_static_ratio_cross.sv)
mut=0; [ "$mode" = mut ] && mut=1
n=0; f=0
for r in "4 3" "3 4"; do set -- $r; ns=$1; nd=$2
  for pw in 0 1 2 3; do for pr in 0 1 2 3; do for rel in 3 6; do
    [ $pw -ge $((12/ns)) ] && continue; [ $pr -ge $((12/nd)) ] && continue
    iverilog -g2012 -s tb_s81_static_ratio_cross -Ptb_s81_static_ratio_cross.NS=$ns -Ptb_s81_static_ratio_cross.ND=$nd \
      -Ptb_s81_static_ratio_cross.PH_W=$pw -Ptb_s81_static_ratio_cross.PH_R=$pr -Ptb_s81_static_ratio_cross.REL=$rel \
      -Ptb_s81_static_ratio_cross.MUT=$mut -o "$out/sim" "${src[@]}"
    n=$((n+1)); if vvp -n "$out/sim" > "$out/r.log" 2>&1 && grep -q "RATIO_STATIC PASS" "$out/r.log"; then :; else f=$((f+1)); [ $mode = pass ] && cat "$out/r.log" | head -5; fi
  done; done; done
done
if [ $mode = pass ]; then
  iverilog -g2012 -s tb_s81_static_ratio_cross -Ptb_s81_static_ratio_cross.SKIPV=1 -o "$out/sim" "${src[@]}"
  vvp -n "$out/sim" | grep "RATIO_STATIC PASS" || f=$((f+1)); n=$((n+1))
  [ $f = 0 ] && echo "RATIO_STATIC_GATE PASS $n runs (all divider phases x 2 releases, 4:3 + 3:4, skipped-phase fault)" || { echo "RATIO_STATIC_GATE FAIL $f/$n"; exit 1; }
else
  [ $f = $n ] && echo "RATIO_STATIC_GATE MUTANT REJECTED $f/$n" || { echo "RATIO_STATIC_GATE MUTANT ESCAPED $((n-f))/$n"; exit 1; }
fi
