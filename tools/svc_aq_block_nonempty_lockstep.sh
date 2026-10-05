#!/bin/bash
set -eu
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "$1")
mkdir "$OUT"
cd "$ROOT"
for pc in 0 1; do
  iverilog -g2012 -s tb_svc_aq_block_nonempty_lockstep \
    -P tb_svc_aq_block_nonempty_lockstep.PULLIN=16 \
    -P tb_svc_aq_block_nonempty_lockstep.AQR=1 \
    -P tb_svc_aq_block_nonempty_lockstep.REFM=1 \
    -P tb_svc_aq_block_nonempty_lockstep.PCI="$pc" \
    -P tb_svc_aq_block_nonempty_lockstep.WQN=4 \
    -P tb_svc_aq_block_nonempty_lockstep.WP=2 \
    -o "$OUT/pc$pc.vvp" \
    rtl/test/hbm_fmax_svc/tb_svc_aq_block_nonempty_lockstep.sv \
    results/rtl/hbm_accel_fmax_inventory_20261004/svc/closure_handoff_20261004/source_snapshots/49fa1b0886e4_ot_hbm_r14_stream_pc.sv \
    rtl/hbm_accel/svc/aq_block_nonempty_cut/ot_hbm_r14_stream_pc_aq_block_nonempty_cut.sv \
    > "$OUT/compile_pc$pc.log" 2>&1
  seed=$((pc+1))
  vvp "$OUT/pc$pc.vvp" +SEED="$seed" +CYC=100000 > "$OUT/pc${pc}_seed${seed}.log" 2>&1
  python3 - "$OUT/pc${pc}_seed${seed}.log" <<'CHECK'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
assert 'cycles=100000 mismatches=0' in s and 'verdict=PASS' in s and 'fault_cycles=0' in s
assert 'MISMATCH' not in s and 'FATAL' not in s
print(s.strip())
CHECK
done
printf '%s\n' 'PASS_BLOCK_NONEMPTY_SOURCE_SEMANTICS 200000 cycles 0 mismatches' > "$OUT/result.txt"
