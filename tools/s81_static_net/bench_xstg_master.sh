#!/usr/bin/env bash
# S-NET production bench of dsfd_xstg_515 (--hend-static).  bench_xstg_master.sh pass|mut_offset MASTER GLUE_SV OUT
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?}; mst=${2:?}; glue=${3:?}; out=${4:?}; mkdir -p "$out"
awk "/^module $mst /,/^endmodule/" "$glue" > "$out/master.sv"
grep -q "ot_s81_static_lane_end" "$out/master.sv" || { echo "XSTG_STATIC FAIL not the static form"; exit 1; }
[ $mode = mut_offset ] && sed -i 's/ot_s81_static_lane_end #(.W(\([0-9]*\)))/ot_s81_static_lane_end #(.W(\1), .OFFSET(3))/' "$out/master.sv"
src=(rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv rtl/dsrom_sys/s81_static_net/ot_s81_static_lane_end.sv "$out/master.sv" rtl/dsrom_sys/s81_static_net/test/tb_dsfd_xstg_static.sv)
f=0; n=0
for ph in 1 4 9; do for tr in 3 11; do
  iverilog -g2012 -DDUT=$mst -DLAT=${XSTG_LAT:-76} -s tb_dsfd_xstg_static -Ptb_dsfd_xstg_static.PHASE=$ph -Ptb_dsfd_xstg_static.TRUNK=$tr -o "$out/sim" "${src[@]}"
  n=$((n+1)); if vvp -n "$out/sim" > "$out/log" 2>&1 && grep -q "XSTG_STATIC PASS" "$out/log"; then grep "XSTG_STATIC PASS" "$out/log"; else f=$((f+1)); grep -m1 -E "XSTG|FATAL" "$out/log"; fi
done; done
if [ $mode = pass ]; then [ $f = 0 ] && echo "XSTG_STATIC_GATE PASS $mst $n runs" || { echo "XSTG_STATIC_GATE FAIL $f/$n"; exit 1; }
else [ $f = $n ] && echo "XSTG_STATIC_GATE MUTANT REJECTED $f/$n" || { echo "XSTG_STATIC_GATE MUTANT ESCAPED"; exit 1; }; fi
