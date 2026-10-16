#!/bin/bash
set -eu
O=$1
mkdir -p "$O"
P=physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_ps_lib.sv
C="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv"
T=results/rtl/svc_eps_pending_20261010/tb_eps_pending.sv
sed "s/spq_d <= ed;/spq_d <= ed ^ (127'd1 << 2);/" "$P" > "$O/mut_tag.sv"
sed "s/(strm ? !spq_v : !pend\[kind\])/(strm ? !spend : !pend[kind])/" "$P" > "$O/mut_hol.sv"
sed "s/if (queue_stream) spq_v <= 1'b1;/if (queue_stream) spq_v <= 1'b0;/" "$P" > "$O/mut_drop.sv"
for M in tag hol drop; do cmp -s "$P" "$O/mut_$M.sv" && exit 2; done
iverilog -g2012 -s tb -o "$O/positive.vvp" $C "$P" "$T"
vvp "$O/positive.vvp" > "$O/positive.log" 2>&1
grep -q 'EPS_RESULT stream=2 W=2 KV=1 IK=1 drops=0' "$O/positive.log"
for M in tag hol drop; do
  iverilog -g2012 -s tb -o "$O/$M.vvp" $C "$O/mut_$M.sv" "$T"
  if vvp "$O/$M.vvp" > "$O/$M.log" 2>&1; then exit 3; fi
  grep -q FATAL "$O/$M.log"
done
iverilog -g2012 -DOT_PS_MUT_CONC -s tb -o "$O/conc.vvp" $C "$P" "$T"
if vvp "$O/conc.vvp" > "$O/conc.log" 2>&1; then exit 4; fi
grep -q STREAM_OVERLAP "$O/conc.log"
echo PASS_EPS_PENDING_4_MUTANTS
