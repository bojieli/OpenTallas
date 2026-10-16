#!/usr/bin/env bash
# H-HARDEN 2026-10-16: lockstep miter of the configured PC controller leaf, QREG=0 (H6 exactly) vs QREG=1 (free-slot
# queue writes, registered push entry, late identity select, controller PHYS_WACT 2), every output on every edge,
# plus four QREG-specific mutants that must be rejected (output mismatch or the push_q == queue[ep] invariant).
#   bench_pc_ctrl_qreg_miter.sh <out>
set -euo pipefail
out=${1:?out}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
src=$d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv; tb=$d/tb_hbm_pc_ctrl_leaf_qreg_miter.sv
base=(rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv
      physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $d/ot_hbm_svc_pc_ctrl_leaf.sv)
iverilog -g2012 -s tb -o "$out/positive.vvp" "${base[@]}" "$src" "$tb" > "$out/positive.build.log" 2>&1
vvp "$out/positive.vvp" > "$out/positive.log" 2>&1
grep 'PC_CTRL_QREG_MITER PASS' "$out/positive.log"
python3 - "$src" "$out" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(); out=Path(sys.argv[2])
m={'no_push_forward':("wire[63:0]push_n=ep_hit?","wire[63:0]push_n=(1'b0)?"),
   'unguarded_free_slot':("if(count+6'(b)<6'd32)queue","if(1'b1)queue"),
   'identity_swap':("(response_take?rid_rp1:rid_rp)","(response_take?rid_rp:rid_rp1)"),
   'stale_ep1':("if(posted)ep1<=ep1+1'b1;","")}
for k,(a,b) in m.items():
    assert s.count(a)==1,(k,a); (out/(k+'.sv')).write_text(s.replace(a,b))
PY
for k in no_push_forward unguarded_free_slot identity_swap stale_ep1; do
  iverilog -g2012 -s tb -o "$out/$k.vvp" "${base[@]}" "$out/$k.sv" "$tb" > "$out/$k.build.log" 2>&1
  if vvp "$out/$k.vvp" +ncyc=3000 > "$out/$k.log" 2>&1; then echo "mutant $k survived"; exit 1; fi
  grep -m1 -E 'QREG (miter|push_q)' "$out/$k.log" | sed "s/^/$k REJECTED: /"
done
echo 'PC_CTRL_QREG_GATE PASS (QREG lockstep miter + 4 mutants rejected)'
