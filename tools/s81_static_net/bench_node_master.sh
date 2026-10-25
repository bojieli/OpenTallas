#!/usr/bin/env bash
# S-NET production bench of a generated static return node master.
#   bench_node_master.sh pass|mut_window|mut_fault|mut_rst|mut_fiunreg MASTER GLUE_SV OUT
# mut_fiunreg (S81-KITS-RTLB 10-24): the fault-chain input ORed into fr straight from the pin again (the pre-fix form).
# mut_window: the master with its node window +1 (sed on the master text); mut_fault: fault chain cut (fo <= flt only);
# mut_rst: the reset pin register never asserts (node flops see no reset).
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?}; mst=${2:?}; glue=${3:?}; out=${4:?}; mkdir -p "$out"
la=0; lb=0; [ "${mst:10:1}" = L ] && la=1; [ "${mst:11:1}" = L ] && lb=1
fch=0; [[ "${mst:12}" == *f* ]] && fch=1
awk "/^module $mst /,/^endmodule/" "$glue" > "$out/master.sv"; grep -q "ot_s81_retn_static" "$out/master.sv" || { echo "NODE_STATIC FAIL master is not the static node"; exit 1; }
case $mode in
  mut_window) sed -i 's/\.WIN(\([0-9]*\))/.WIN(9\1)/; s/\.WIN(92)/.WIN(3)/; s/\.WIN(91)/.WIN(2)/' "$out/master.sv";;
  mut_rst) grep -q "reg rn;" "$out/master.sv" || { echo "NODE_STATIC FAIL mut_rst needs the reset pin register"; exit 1; }
           sed -i "s/if (!rst_n\[0\]) rn <= 1'b0; else rn <= 1'b1;/rn <= 1'b1;/" "$out/master.sv";;
  mut_fault) sed -i 's/fr <= flt | fi\[0\];/fr <= 1'"'"'b0;/; s/fr <= flt | fil;/fr <= 1'"'"'b0;/; s/fr <= flt;/fr <= 1'"'"'b0;/' "$out/master.sv";;
  mut_fiunreg) grep -q 'fr <= flt | fil;' "$out/master.sv" || { echo "NODE_STATIC FAIL mut_fiunreg needs the fi pin register"; exit 1; }
           sed -i 's/fr <= flt | fil;/fr <= flt | fi[0];/' "$out/master.sv";;
esac
win=$(grep -o '\.WIN([0-9]*)' "$out/master.sv" | head -1 | tr -dc 0-9); [ "$mode" != pass ] && win=$(grep -o '\.WIN([0-9]*)' "$glue" | head -1 | tr -dc 0-9)
src=(rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv
     "$out/master.sv" rtl/dsrom_sys/s81_static_net/test/tb_dsfd_node_static.sv)
defs="-DDUT=$mst"; [ $la = 1 ] && defs="$defs -DLA"; [ $lb = 1 ] && defs="$defs -DLB"; [ $fch = 1 ] && defs="$defs -DHAS_FI"
fails=0; runs=0
for s in 1 2 3 4 c; do
  d="$out/v_$s"; c=""; seed=$s; [ $s = c ] && { c=--collide; seed=5; }
  python3 tools/s81/static_return_calendar.py vectors --win "$win" --rst 1 --seed $seed --words 400 $c $( [ $la = 1 ] && echo --leaf-a ) $( [ $lb = 1 ] && echo --leaf-b ) --out "$d" > "$d.gen.log"
  iverilog -g2012 $defs -s tb_dsfd_node_static -o "$d.sim" "${src[@]}"
  runs=$((runs+1))
  if vvp -n "$d.sim" +DIR="$d" +T="$(cat $d/T)" +FAULT="$(cat $d/FAULT)" > "$d.log" 2>&1 && grep -q "NODE_STATIC PASS" "$d.log"; then grep "NODE_STATIC PASS" "$d.log"; else fails=$((fails+1)); grep -m2 "NODE_STATIC" "$d.log" || tail -2 "$d.log"; fi
done
if [ $mode = pass ]; then [ $fails = 0 ] && echo "NODE_STATIC_GATE PASS $mst $runs runs (win $win, leaf a/b $la/$lb, fault chain $fch)" || { echo "NODE_STATIC_GATE FAIL $fails/$runs"; exit 1; }
else [ $fails -gt 0 ] && echo "NODE_STATIC_GATE MUTANT $mode REJECTED $fails/$runs" || { echo "NODE_STATIC_GATE MUTANT $mode ESCAPED"; exit 1; }; fi
