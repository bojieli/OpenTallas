#!/usr/bin/env bash
# S-NET status-lane pair bench (--hend-static): start dsfd_l2r_vs<F>_1x1__hs_<x> + end dsfd_m2l_vs<F>_1x1__he_<x>.
#   bench_status_master.sh pass|mut_offset MASTER GLUE_SV OUT   (MASTER = either side; the partner is found by name)
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?}; mst=${2:?}; glue=${3:?}; out=${4:?}; mkdir -p "$out"
sfx=${mst#*__h?_}; F=$(echo "$mst" | sed -E 's/.*_vs([01])_.*/\1/')
s=$(grep -o "^module dsfd_l2r_vs${F}_1x1__hs_${sfx} " "$glue" "$(dirname "$glue")"/*.sv 2>/dev/null | head -1 | awk '{print $2}'); e=$(grep -o "^module dsfd_m2l_vs${F}_1x1__he_${sfx} " "$glue" "$(dirname "$glue")"/*.sv 2>/dev/null | head -1 | awk '{print $2}')
[ -n "$s" ] && [ -n "$e" ] || { echo "STATUS_STATIC FAIL partner of $mst not found"; exit 1; }
cat "$glue" "$(dirname "$glue")"/dsfd_l2r_vs${F}_1x1__hs_${sfx}.sv "$(dirname "$glue")"/dsfd_m2l_vs${F}_1x1__he_${sfx}.sv 2>/dev/null > "$out/all.sv" || true
awk "/^module $s /,/^endmodule/" "$out/all.sv" | awk 'BEGIN{n=0} /^module/{n++} n==1' > "$out/s.sv"
awk "/^module $e /,/^endmodule/" "$out/all.sv" | awk 'BEGIN{n=0} /^module/{n++} n==1' > "$out/e.sv"
grep -qE "ot_meso_fifo|ot_ratio_cdc_fifo" "$out/s.sv" "$out/e.sv" && { echo "STATUS_STATIC FAIL FIFO still present"; exit 1; }
nxs=$(( ($(grep -o "input wire \[[0-9]*:0\] xf" "$out/s.sv" | grep -o "[0-9]*" | head -1) + 1) / 2 ))
nxe=$(( ($(grep -o "input wire \[[0-9]*:0\] xf" "$out/e.sv" | grep -o "[0-9]*" | head -1) + 1) / 2 ))
src=(rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv rtl/dsrom_sys/s81_static_net/ot_s81_static_lane_end.sv rtl/dsrom_sys/s81_static_net/ot_s81_static_ratio_cross.sv "$out/s.sv" "$out/e.sv" rtl/dsrom_sys/s81_static_net/test/tb_dsfd_status_static.sv)
run() { iverilog -g2012 -DDUT_S=$s -DDUT_E=$e -s tb_dsfd_status_static -Ptb_dsfd_status_static.F=$F -Ptb_dsfd_status_static.NXS=$nxs -Ptb_dsfd_status_static.NXE=$nxe -o "$out/sim" "${src[@]}" && vvp -n "$out/sim"; }
ref=$(run | grep "STATUS_STATIC PASS" || true)
if [ $mode = pass ]; then [ -n "$ref" ] && { echo "$ref"; echo "STATUS_STATIC_GATE PASS $s -> $e"; } || { run | tail -3; echo "STATUS_STATIC_GATE FAIL"; exit 1; }; exit 0; fi
case $mst in
  dsfd_l2r_*) sed -i 's/reg \[1:0\] i_q; always @(posedge ck\[0\]) i_q <= i;/wire [1:0] i_q = i;/' "$out/s.sv";;   # start: input pin flop removed
  *) sed -i 's/ot_s81_static_lane_end #(.W(\([0-9]*\)))/ot_s81_static_lane_end #(.W(\1), .OFFSET(3))/' "$out/e.sv";;
esac
got=$(run | grep "STATUS_STATIC PASS" || true)
if [ "$got" != "$ref" ]; then echo "STATUS_STATIC_GATE MUTANT REJECTED [$got] vs [$ref]"; else echo "STATUS_STATIC_GATE MUTANT ESCAPED"; exit 1; fi
