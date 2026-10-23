#!/bin/bash
# kvs_grp_r2_bench.sh OUT grp|grp_h [MUT=0] [GRP=n] [EDGES=4000] [struct] (KDIE5-RTL 10-22): lockstep equivalence of the
# pin-registered group successors (rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_r2.sv) against the unchanged release
# module on delayed inputs (tb/tb_qkd_kvs_grp_r2_eq.sv), Verilator 5.050.  One GRP_R2 line; exit 0 only on PASS.
set -u
O=$1; K=$2; M=${3:-0}; G=${4:-}; E=${5:-4000}
[ "${6:-}" = struct ] && STRUCT=1     # 6th argument "struct" = STRUCT=1
mkdir -p "$O"
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
D=rtl/qwen_sys/static_kv_20261014
SRC="rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_r2.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv
 $D/qkd_kv_cfault_tree.sv $D/qkd_kv_front_cal.sv $D/qkd_kv_landing_cal.sv $D/qkd_static_kv_boot_cdc.sv $D/qkd_static_kv_hop.sv
 $D/qkd_static_kv_landing.sv $D/qkd_static_kv_landing_seg.sv $D/qkd_static_kv_ownership.sv $D/qkd_static_kv_phase_launch.sv
 rtl/qwen_sys/static_kv_die_20261017/tb/tb_qkd_kvs_grp_r2_eq.sv"
DEF=""; [ "$K" = grp_h ] && DEF="+define+GRP_H"
if [ -n "${STRUCT:-}" ]; then
  # STRUCT=1: the DUT is the bounded-driver structural copy (qkd_kvs_grp{,_h}_r2c.sv, mapped cells on the PDK library
  # model); the reference stays the release RTL; mutants are output mutants (tb OM=n)
  # Initial state: the reference RTL starts every register at 0 (Verilator --x-initial 0); a mapped flop holds QN = ~state,
  # so the bench-local copy of the PDK model starts the two flop cells the netlist uses at QN = 1 (= state 0), i.e. the
  # SAME initial state on both sides (unreset configuration registers would otherwise start at all-ones in the DUT only)
  LIBM=$O/library_model_pdk_q0.v
  sed -e 's/^module DFFHQNx1_ASAP7_75t_R(input CLK,D,output reg QN);/module DFFHQNx1_ASAP7_75t_R(input CLK,D,output reg QN = 1'"'"'b1);/' \
      -e 's/^module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);/module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN = 1'"'"'b1);/' \
      results/rtl/qwen_kv_die/canonical_seq_coupon_1020/formal_compatible/library_model_pdk.v > "$LIBM"
  [ "$(grep -c "output reg QN = 1'b1)" "$LIBM")" = 2 ] || { echo "GRP_R2 FAIL tile=$K mut=$M library-model init patch"; exit 1; }
  SRC="$(echo "$SRC" | sed 's#rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_r2.sv##') rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_${K}_r2c.sv $LIBM"
  DEF="$DEF +define+DUT_G=qkd_kvs_grp_r2c +define+DUT_H=qkd_kvs_grp_h_r2c +define+OM=$M"
else
  [ "$M" != 0 ] && DEF="$DEF +define+KVS_GRP_R2_MUT$M"
fi
B=$O/obj_${K}_m$M
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb $DEF \
  -Mdir "$B" -o vtb $SRC > "$O/build_${K}_m$M.log" 2>&1 || { tail -20 "$O/build_${K}_m$M.log"; echo "GRP_R2 FAIL tile=$K mut=$M build"; exit 1; }
# GRP=all: every strap the die ties (grp: slg index 0..7 except the chain end 4 is grp_h; grp_h: 4); one summary line
if [ "$G" = all ]; then GS=$([ "$K" = grp_h ] && echo 4 || echo 7 6 3 2 1 0 5); else GS=${G:-def}; fi
tot=0; bad=0
for g in $GS; do
  L=$O/run_${K}_m${M}_g$g.log
  if [ "$g" = def ]; then "$B/vtb" +EDGES=$E > "$L" 2>&1; else "$B/vtb" +GRP=$g +EDGES=$E > "$L" 2>&1; fi
  grep -m3 MISMATCH "$L"
  line=$(grep '^GRP_R2 ' "$L" | tail -1); echo "  $line"
  case "$line" in "GRP_R2 PASS"*) ;; *) bad=$((bad + 1));; esac
  c=$(echo "$line" | sed -n 's/.*checks=\([0-9]*\).*/\1/p'); tot=$((tot + ${c:-0}))
done
v=PASS; [ $bad -ne 0 ] && v=FAIL
echo "GRP_R2 $v tile=${K}_r2${STRUCT:+c} straps=$(echo $GS | wc -w) failing=$bad checks=$tot mut=$M"
[ $v = PASS ]
