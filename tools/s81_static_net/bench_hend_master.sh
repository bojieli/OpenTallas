#!/usr/bin/env bash
# S-NET production bench of a generated hub end / start block (--hend-static).
#   bench_hend_master.sh pass|mut_offset MASTER GLUE_SV OUT [LAT]
# pass: 3 lane phases, every edge exact, first-word latency locked to LAT (if given) and constant over phases;
# mut_offset: the crossing offset / mapping changed by one (lane end OFFSET 3, ratio cross MUT 1) -> must FAIL.
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?}; mst=${2:?}; glue=${3:?}; out=${4:?}; lat=${5:--1}; mkdir -p "$out"
awk "/^module $mst /,/^endmodule/" "$glue" > "$out/master.sv"
if [ $mode = mut_offset ]; then   # reference: the unmutated master's per-phase first-word latencies
  ref=$(bash "$0" pass "$mst" "$glue" "$out/ref" | tail -1 | grep -o 'latency [0-9-]*' | tr '\n' ' ')
  [ -n "$ref" ] || { echo "HEND_STATIC_GATE FAIL reference run"; exit 1; }
fi
grep -qE "ot_meso_fifo|ot_ratio_cdc_fifo" "$out/master.sv" && { echo "HEND_STATIC FAIL credit/ratio FIFO still in $mst"; exit 1; }
if [ $mode = mut_offset ]; then
  sed -i 's/ot_s81_static_lane_end #(.W(\([0-9]*\)))/ot_s81_static_lane_end #(.W(\1), .OFFSET(3))/; s/ot_s81_static_ratio_cross #(\(.W([0-9]*)\)/ot_s81_static_ratio_cross #(\1, .MUT(1)/' "$out/master.sv"
  grep -q "same-clock\|ot_s81_static" "$out/master.sv" || true
  if ! grep -qE "OFFSET\(3\)|MUT\(1\)" "$out/master.sv"; then  # same-clock start: shift the pin pipeline by one stage
    sed -i 's/od_q <= {w_\[/od_q <= {i[/; s/w_\[0\] \& rsl/i[0] \& rsl/' "$out/master.sv"
  fi
fi
defs="-DDUT=$mst"; nl=1; pw=0
case $mst in
  dsfd_m2l_*) defs="$defs -DM2L"; nl=$(grep -c "input wire \[0:0\] fi" "$out/master.sv")
     dw=$(grep -o "input wire \[[0-9]*:0\] di0" "$out/master.sv" | grep -o "[0-9]*" | head -1); dw=$((dw+1))
     ports=""; for j in $(seq 0 $((nl-1))); do ports="$ports, .di$j(di[$j*DW +: DW]), .fi$j(fi[$j])"; done
     if [[ $mst == dsfd_m2l_raw_* ]]; then defs="$defs -DRAW"; pw=$dw; else pw=$((dw-2)); fi;;
  dsfd_r2l_*) defs="$defs -DR2L"; dw=$(grep -o "input wire \[[0-9]*:0\] di0" "$out/master.sv" | grep -o "[0-9]*" | head -1); pw=$((dw+1-2)); ports=", .di0(di[DW-1:0]), .fi0(fi[0])";;
  dsfd_l2r_*) defs="$defs -DL2R"; w=$(grep -o "input wire \[[0-9]*:0\] i," "$out/master.sv" | grep -o "[0-9]*" | head -1); pw=$w; ports=""
     grep -q "ot_s81_static_ratio_cross" "$out/master.sv" && defs="$defs -DRATIO"
     grep -q "output wire \[2:0\] st" "$out/master.sv" && defs="$defs -DHAS_ST";;
esac
src=(rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv rtl/dsrom_sys/s81_static_net/ot_s81_static_lane_end.sv
     rtl/dsrom_sys/s81_static_net/ot_s81_static_ratio_cross.sv "$out/master.sv" rtl/dsrom_sys/s81_static_net/test/tb_dsfd_hend_static.sv)
f=0; n=0; lats=""
for ph in 0 4 9; do
  iverilog -g2012 $defs "-DPORTS=$ports" -s tb_dsfd_hend_static -Ptb_dsfd_hend_static.NL=$nl -Ptb_dsfd_hend_static.PW=$pw \
    -Ptb_dsfd_hend_static.PH=$ph -Ptb_dsfd_hend_static.LAT=$lat -o "$out/sim" "${src[@]}"
  n=$((n+1)); if vvp -n "$out/sim" > "$out/log$ph" 2>&1 && grep -q "HEND_STATIC PASS" "$out/log$ph"; then grep "HEND_STATIC PASS" "$out/log$ph"; lats="$lats $(grep -o 'latency [0-9-]*' $out/log$ph | head -1)"; else f=$((f+1)); grep -m2 "HEND" "$out/log$ph" || tail -2 "$out/log$ph"; fi
done
if [ $mode = pass ]; then [ $f = 0 ] && echo "HEND_STATIC_GATE PASS $mst lanes $nl x $pw b,$lats" || { echo "HEND_STATIC_GATE FAIL $f/$n"; exit 1; }
else
  got=$(echo $lats | tr '\n' ' ')
  if [ $f -gt 0 ] || [ "$(echo $got)" != "$(echo $ref)" ]; then echo "HEND_STATIC_GATE MUTANT REJECTED fails $f/$n, latencies [$got] vs [$ref]"
  else echo "HEND_STATIC_GATE MUTANT ESCAPED"; exit 1; fi
fi
