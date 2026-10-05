#!/bin/bash
# Existing s4 stimulus/oracle, target AQ geometry only. No runtime deadlines.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "$1")
mkdir "$OUT"
cd "$ROOT"
for pc in 0 1; do
  iverilog -g2012 -s tb_svc_aq_act_cut_lockstep \
    -P tb_svc_aq_act_cut_lockstep.PULLIN=16 \
    -P tb_svc_aq_act_cut_lockstep.AQR=1 \
    -P tb_svc_aq_act_cut_lockstep.REFM=1 \
    -P tb_svc_aq_act_cut_lockstep.PCI="$pc" \
    -P tb_svc_aq_act_cut_lockstep.WQN=4 \
    -P tb_svc_aq_act_cut_lockstep.WP=2 \
    -o "$OUT/pc$pc.vvp" \
    rtl/test/hbm_fmax_svc/tb_svc_aq_act_cut_lockstep.sv \
    results/rtl/hbm_accel_fmax_inventory_20261004/svc/closure_handoff_20261004/source_snapshots/49fa1b0886e4_ot_hbm_r14_stream_pc.sv \
    rtl/hbm_accel/svc/aq_act_cut/ot_hbm_r14_stream_pc_aq_act_cut.sv \
    > "$OUT/compile_pc$pc.log" 2>&1
  for seed in 1 2; do
    vvp "$OUT/pc$pc.vvp" +SEED="$seed" +CYC=400000 > "$OUT/pc${pc}_seed${seed}.log" 2>&1
    python3 - "$OUT/pc${pc}_seed${seed}.log" <<'PY'
import sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
assert 'MISMATCH' not in s and 'cycles=400000 mismatches=0' in s and 'verdict=PASS' in s, s[-2500:]
print(s.strip().splitlines()[-1])
PY
  done
done
printf '%s\n' 'PASS_SOURCE_EXACT_AQ_TARGET 1600000 cycles 0 mismatches' > "$OUT/result.txt"
