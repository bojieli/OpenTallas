#!/bin/bash
# run_head_mtp.sh  (cwd = repo root / worktree)  TOK-FUNC-S81/HEADMTP, tree lines TOK.DS.LAYER.5 (LM head) + TOK.DS.LAYER.6 (MTP)
# One command: HEAD goldens (light, local) -> stage sources + goldens + fixture subsets on a fleet host -> ot-run
# head_mtp_fleet.sh (all Verilator 5.050 builds/sims on the fleet) -> fetch logs -> results/token_pass/tokfunc_s81_1021/head_mtp.json
# Env: HEAD_FIX (default /home/ubuntu/scratch/layerbench-s81/fixtures/HEAD), MTP_FIX (default the regenerated 10-18 MTP fixture
# /home/ubuntu/scratch/lb2-s81-mtp/MTP; the layerbench-s81/fixtures/MTP copy is empty: its generator run hit the embed-row
# KeyError fixed in main), HOST (staging host, default ot-epyc7), LANE_DIR (remote), LOCAL (local scratch), NOFLEET=1 (report only).
set -eu
R=$(pwd); HEAD_FIX=${HEAD_FIX:-/home/ubuntu/scratch/layerbench-s81/fixtures/HEAD}; MTP_FIX=${MTP_FIX:-/home/ubuntu/scratch/lb2-s81-mtp/MTP}
HOST=${HOST:-ot-epyc7}; LANE_DIR=${LANE_DIR:-/srv/opentallas-scratch/claude/tokfunc-s81-headmtp}
LOCAL=${LOCAL:-/home/ubuntu/scratch/tokfunc-s81-headmtp}; RUN=run_$(date +%m%d_%H%M)
OUT=${OUT:-results/token_pass/tokfunc_s81_1021/head_mtp.json}
mkdir -p $LOCAL
python3 tools/s81_dv/tokfunc/head_mtp_gold.py --head $HEAD_FIX --out $LOCAL/prep
if [ "${NOFLEET:-0}" != 1 ]; then
  ssh $HOST "mkdir -p $LANE_DIR/src $LANE_DIR/fix/HEAD/ops $LANE_DIR/fix/HEAD/io $LANE_DIR/fix/HEAD/weights $LANE_DIR/fix/MTP/ops"
  tar -C $R -cf - --exclude=.git rtl tools physical results/arch compiler | ssh $HOST "tar -C $LANE_DIR/src -xf -"
  rsync -a --delete $LOCAL/prep/ $HOST:$LANE_DIR/prep/
  rsync -a $HEAD_FIX/files.json $HEAD_FIX/meta.json $HOST:$LANE_DIR/fix/HEAD/
  rsync -a $HEAD_FIX/ops/head.norm.scale.bin $HEAD_FIX/ops/head.lm_head.bin $HOST:$LANE_DIR/fix/HEAD/ops/
  rsync -a $HEAD_FIX/io/next_token.bin $HOST:$LANE_DIR/fix/HEAD/io/
  rsync -a $HEAD_FIX/weights/head.bin $HOST:$LANE_DIR/fix/HEAD/weights/
  rsync -a $MTP_FIX/files.json $MTP_FIX/meta.json $HOST:$LANE_DIR/fix/MTP/
  rsync -a $(ls $MTP_FIX/ops/draft.head?.bin $MTP_FIX/ops/draft.head?.norm.scale.bin $MTP_FIX/ops/draft.markov?.bin \
             $MTP_FIX/ops/draft.markov?.logits.bin $MTP_FIX/ops/draft.markov?.token.bin) $HOST:$LANE_DIR/fix/MTP/ops/
  set +e
  /home/ubuntu/bin/ot-run --mem ${MEM:-120} --threads ${THREADS:-48} --dir $LANE_DIR/src -- \
    bash tools/s81_dv/tokfunc/head_mtp_fleet.sh $LANE_DIR/prep $LANE_DIR/fix $LANE_DIR/$RUN > $LOCAL/$RUN.otrun.log 2>&1
  echo "ot-run exit $?"; tail -3 $LOCAL/$RUN.otrun.log
  set -e
  EXEC=$(grep -oE "RAN on [a-z0-9-]+" $LOCAL/$RUN.otrun.log | awk '{print $3}' | tail -1); EXEC=${EXEC:-$HOST}
  mkdir -p $LOCAL/$RUN
  rsync -a --exclude='obj*' --exclude='*.viamap.hex' --exclude='*.o' $EXEC:$LANE_DIR/$RUN/ $LOCAL/$RUN/
  echo "$RUN" > $LOCAL/LAST_RUN
fi
RUNDIR=$LOCAL/$(cat $LOCAL/LAST_RUN)
python3 tools/s81_dv/tokfunc/head_mtp_report.py --run $RUNDIR --prep $LOCAL/prep --out $OUT \
  --meta run_dir=$RUNDIR host_dir=$LANE_DIR branch=$(git rev-parse --abbrev-ref HEAD) commit=$(git rev-parse --short=9 HEAD)
