#!/usr/bin/env bash
# TOKSIM-HBM-smhbm (10-19): fleet driver of toksim_smhbm.py (SM.MATVEC + HBM stream on the GEN2e3 die composition).
#   run_toksim_smhbm.sh sync REV                 archive REV's sources into $SRC (ot-epyc5; smw copied in $L/smw)
#   run_toksim_smhbm.sh run NAME LAYERS [ENV...] one ot-run job: build (cached per REV) + run; out/NAME.{json,log}
# ENV = smb_unit knobs, e.g. SMB_PACE_NUM=200 SMB_PACE_DEN=64 SMB_PACE_ADD=8 SMB_FETCH=200 SMB_OP_GAP=256 SMB_CENSUS_R=1
set -uo pipefail
L=${L:-/srv/opentallas-scratch/claude/toksim-smhbm-1019}; HOST=${HOST:-ot-epyc5}; SRC=${SRC:-$L/src}
MODE=$1; shift
if [ "$MODE" = sync ]; then
  REV=$1; WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$WT" rev-parse "$REV")
  ssh "$HOST" "mkdir -p $SRC $L/out $L/work && rm -rf $SRC/*" || exit 2
  git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hdc_golden_v41.py tools/hdc_golden.py tools/rtl_gpu_sm_exact.py \
    tools/rtl_hdc_v41_blockdot_campaign.py tools/hbm_svc_packed136_image.py tools/w19_payload_loader.py tools/dshbm_matched_sm_seq.py tools/hgi_sim \
    rtl/hbm_accel rtl/lib rtl/model_ready_hbm_r14 rtl/gpu rtl/hdc rtl/v41rom rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv \
    rtl/test/hbm_accel/svg_rel physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 \
    physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 \
    physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1 physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192 results/rtl/hbm_ds_layer_tput_1018/fixtures/L00 \
    results/rtl/hbm_ds_layer_tput_1018/fixtures/L02 results/rtl/hbm_ds_layer_tput_1018/fixtures/L14 \
    results/rtl/hbm_ds_layer_tput_1018/fixtures/head | ssh "$HOST" "tar -x -C $SRC" || exit 2
  echo "$SHA" | ssh "$HOST" "cat > $SRC/REV"; echo "SYNC $SHA"; exit 0
fi
NAME=$1; LAYERS=$2; shift 2; ENVS="$*"
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
J="cd $SRC && export $VL HDC_V41_ARITH=chunk8 $ENVS && flock $L/work/build.lock python3 -c 'import sys;sys.argv=[\"x\"];sys.path.insert(0,\"tools/hbm_layer_vehicle\");import toksim_smhbm as T;from pathlib import Path;T.build(Path(\"$L/work\"),None,[])' > $L/out/build_$NAME.log 2>&1; python3 tools/hbm_layer_vehicle/toksim_smhbm.py run --fix $SRC/results/rtl/hbm_ds_layer_tput_1018/fixtures --smw $L/smw --work $L/work --layers $LAYERS --name $NAME --out $L/out/$NAME.json > $L/out/$NAME.log 2>&1; echo ${NAME}_RC \$?; tail -n 2 $L/out/$NAME.log"
/home/ubuntu/bin/ot-run --mem ${MEM:-48} --threads 16 --dir "$L" -- bash -c "$J"
echo "TOKSIM_SMHBM_DONE $NAME"
