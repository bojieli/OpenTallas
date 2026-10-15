#!/bin/bash
# run_vm_ring.sh <tile> <out dir> [verilator]: [vm8cp] shared ring-transport bench (tb_vm_ring.sv) on ONE exact ring / relay
# tile module of physical/hbm_accel_die_views/vm/cp/rtl.  Tiles: rt rt2 rb rb2 rwa rwb.  Seeds 1 and 2 must both pass.
#   VM_RING_MUT=<DROP|ADDR|CREDIT|FORK>  build the DUT from a mutated COPY of the tile RTL (the routed file is untouched):
#     DROP    lane A flop loses the valid bit of the beats whose sequence byte is 0x77 (dropped beat)
#     ADDR    lane A flop swaps station-address bits 0/1 (beat for the wrong station)
#     CREDIT  lane B's top credit bit is refreshed only every other clock (stale credit; two-way tiles only)
#     FORK    the station fork taps lane B one bit off (rb2 rd / rt2 cfg only)
#   VM_RING_BEATS=<n>  beat target (default 20000); below 20000 the bench REFUSES to pass (coverage refusal, bench "vacuous")
# The lane table below is the plan of make_vm_cp.py's relay tiles and is NOT read from the tile RTL: a tile whose ports,
# widths or bit map differ fails to build or fails "exact".
T=${1:?tile}; O=${2:?out}; VL=${3:-verilator}; C=physical/hbm_accel_die_views/vm/cp; R=$C/ring; mkdir -p $O
case $T in
  rt)  WA=2048; WB=2048; WF=0;   P=".wi(a_i), .eo(a_o), .ei(b_i), .wo(b_o)"; LA=eo; LB=wo; LF=;;
  rt2) WA=2048; WB=2048; WF=1;   P=".wi(a_i), .eo(a_o), .ei(b_i), .wo(b_o), .cfg(f_o)"; LA=eo; LB=wo; LF=cfg;;
  rb)  WA=2048; WB=1078; WF=0;   P=".wi(a_i), .eo(a_o), .ei(b_i), .wo(b_o)"; LA=eo; LB=wo; LF=;;
  rb2) WA=2048; WB=1078; WF=201; P=".wi(a_i), .eo(a_o), .ei(b_i), .wo(b_o), .rd(f_o)"; LA=eo; LB=wo; LF=rd;;
  rwa) WA=2048; WB=0;    WF=0;   P=".i(a_i), .o(a_o)"; LA=o; LB=; LF=;;
  rwb) WA=217;  WB=0;    WF=0;   P=".i(a_i), .o(a_o)"; LA=o; LB=; LF=;;
  *) echo "unknown ring tile $T"; exit 2;;
esac
SRC=$C/rtl/vm_cp_$T.sv; DUT=$SRC; MUT=${VM_RING_MUT:-}; BEATS=${VM_RING_BEATS:-20000}
echo "VM_RING_SRC tile=$T sha256=$(sha256sum $SRC | cut -c1-64) mut=${MUT:-none}"
if [ -n "$MUT" ]; then
  DUT=$O/vm_cp_${T}_mut_$MUT.sv
  python3 $R/ring_mut.py $SRC $DUT $MUT "$LA" "$LB" "$LF" $WB || { echo "VM_RING_BENCH ERROR mutant $MUT not applicable to $T"; exit 3; }
fi
WBX=$(( WB > 0 ? WB : 1 )); WFX=$(( WF > 0 ? WF : 1 ))
{ echo "module ring_dut (input wire ck, input wire [$((WA-1)):0] a_i, output wire [$((WA-1)):0] a_o, input wire [$((WBX-1)):0] b_i, output wire [$((WBX-1)):0] b_o, output wire [$((WFX-1)):0] f_o);"
  echo "    vm_cp_$T u_tile (.ck(ck), $P);"
  [ $WB = 0 ] && echo "    assign b_o = '0;"; [ $WF = 0 ] && echo "    assign f_o = '0;"
  echo "endmodule"; } > $O/ring_dut.sv
$VL --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_vm_ring -DWA=$WA -DWB=$WB -DWF=$WF \
  -Mdir $O/obj -o sim rtl/common/ot_fwd_link_stage.sv $DUT $O/ring_dut.sv $R/tb_vm_ring.sv > $O/build.log 2>&1 \
  || { echo "VM_RING_BENCH FAIL tile=$T: BUILD_FAILED"; grep -m8 -iE "error" $O/build.log; exit 1; }
ok=1; n=0
for s in 1 2; do
  $O/obj/sim +verilator+seed+$s +tile=$T +beats=$BEATS > $O/s$s.log 2>&1
  grep -E "^VM_RING" $O/s$s.log
  grep -q "^VM_RING_RUN PASS tile=$T " $O/s$s.log && ! grep -q "VM_RING_RUN FAIL" $O/s$s.log || ok=0
  b=$(sed -n 's/^VM_RING_RUN PASS .*beats=\([0-9]*\).*/\1/p' $O/s$s.log); n=$(( n + ${b:-0} ))
done
if [ $ok = 1 ] && [ $n -gt 0 ]; then echo "VM_RING_BENCH PASS tile=$T mut=${MUT:-none} beats=$n/1"; else echo "VM_RING_BENCH FAIL tile=$T mut=${MUT:-none} beats=$n/1"; exit 1; fi
