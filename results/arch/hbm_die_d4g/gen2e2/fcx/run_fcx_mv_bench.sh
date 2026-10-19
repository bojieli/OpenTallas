#!/usr/bin/env bash
# LH-GEN2E-IN 10-19: SM.MATVEC (normal mode: the BE combine tree sums the four tile rows) on the die SM master with the
# fc_xr2 swap, from the real DS layer fixture (tools/hbm_layer_vehicle/sm_mv_unit.py, Verilator 5.050, fleet).
# The SM master files are THIS revision's (bundle = the GEN2b swx2b master list + ot_hbm_accel_smh_fc_xr2.sv).
#   pos  records 4 (wq_a FP8 R=1), 30 (wo_a BF16 K-split R=32), 42 (router gate BF16)   -> PASS
#   mut  same records, SM_MV_EXTRA_DEFINES=OT_SMH_FCX_MUT_NOALIGN (fc_xr2 without the tile-row-0 landing) -> FAIL
# usage: run_fcx_mv_bench.sh REV [HOST] [OUT]
set -uo pipefail
REV=$1; HOST=${2:-ot-epyc5}; OUT=${3:-/srv/opentallas-scratch/claude/lh-gen2e-in/fcx_mv}
SRCB=/srv/opentallas-scratch/claude/layerbench-hbm/swx2b; SMW=/srv/opentallas-scratch/claude/layerbench-hbm/dsfix/smw/L00
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator HDC_V41_ARITH=chunk8'
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out && rm -rf $OUT/src/* $OUT/bundle" || exit 2
git -C "$WT" archive "$SHA" tools rtl/hdc rtl/gpu rtl/lib rtl/v41rom rtl/hbm_accel/sm rtl/hbm_accel/epilogue \
  rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  results/rtl/hbm_ds_layer_tput_1018/fixtures/L00 | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
# bundle: the GEN2b master list for ot_hbm_accel_smh_attn, every file from THIS revision, + fc_xr2 (u_rw / u_re master)
ssh "$HOST" "cd $OUT && python3 - <<'PY'
import json, shutil
from pathlib import Path
m = json.load(open('$SRCB/master_files.json'))['ot_hbm_accel_smh_attn']
m = m + ['rtl/hbm_accel/sm/ot_hbm_accel_smh_fc_xr2.sv']
for f in m:
    d = Path('bundle') / f; d.parent.mkdir(parents=True, exist_ok=True); shutil.copy(Path('src') / f, d)
json.dump({'ot_hbm_accel_smh_attn': m}, open('bundle/master_files.json', 'w'), indent=1)
print('bundle files', len(m))
PY" || exit 2
T="cd $OUT/src && $VL python3 tools/hbm_layer_vehicle/sm_mv_unit.py run --fixtures $OUT/src/results/rtl/hbm_ds_layer_tput_1018/fixtures/L00 --weights $SMW --bundle $OUT/bundle --recs 4,30,42 --sm0-only"
R=/home/ubuntu/bin/ot-run
$R --mem 48 --threads 16 --dir "$OUT" -- bash -c "$T --work $OUT/wpos --out $OUT/out/mv_pos.json > $OUT/out/mv_pos.log 2>&1; echo MV_POS_RC \$?" \
  > /tmp/lhgen2ein_mv_pos.out 2>&1 &
P1=$!
$R --mem 48 --threads 16 --dir "$OUT" -- bash -c "SM_MV_EXTRA_DEFINES=OT_SMH_FCX_MUT_NOALIGN $T --work $OUT/wmut --out $OUT/out/mv_noalign.json > $OUT/out/mv_noalign.log 2>&1; echo MV_NOALIGN_RC \$?" \
  > /tmp/lhgen2ein_mv_mut.out 2>&1 &
P2=$!
wait $P1 $P2
echo FCX_MV_BENCH_DONE
