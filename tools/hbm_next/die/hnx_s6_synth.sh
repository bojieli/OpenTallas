#!/bin/bash
# HBM-NEXT-DIE 10-19: synth the relay/landing masters the DIE-P4-1 chain reported SYNTH_MISSING at S6, in the GEN2 S6
# synth_round form (tools/hbm_die_v15 synth_master.sh HIER=1 + synth_etm.sh, wrapper-only EXTRA as GEN2's drive records),
# at NORMAL priority (v16_synth_drive.py hard-codes --priority die and a whole-commit git grep, so it is not used here),
# then v16_fetch.py (source bytes checked against the case src commit), upload the views into the case vplan and rerun
# the chain FROM=S6.   local driver:  nohup bash hnx_s6_synth.sh CELL... >> $A/chain.log 2>&1 &
set -o pipefail
B=/srv/opentallas-scratch/claude/hnx/die_p4; A=/home/ubuntu/artifacts/hnx/die_p4; W=/home/ubuntu/wt/hnx-die-1019
OTRUN=/home/ubuntu/bin/ot-run; SRC_COMMIT=${SRC_COMMIT:-42726f987}; V=$A/vplan_s6; MEMG=${MEMG:-8}
echo "STEP S6S synth_missing $(date -Is) cells: $*"
mkdir -p $V/drive
for c in "$@"; do
  w=$(awk -F'\t' -v c=$c '$1==c{print $3}' $V/jobs.tsv); m=$(awk -F'\t' -v c=$c '$1==c{print $2}' $V/jobs.tsv)
  [ -n "$w" ] || { echo "S6S_NO_JOB_ROW $c"; exit 21; }
  # GEN2's view rows give the lh0_/land0_ masters LIBCELLS=1 (their ot_hdc_cg instantiates the ASAP7 ICG cell directly); the hnx
  # vplan rows lost that env, so it is restored here for those masters.
  LC=""; case $c in hbfd_lh0_*|hbfd_land0_*) LC="LIBCELLS=1";; esac
  # a cell whose synth + ETM already finished (etm rc=0 in its r0 log) is not rebuilt
  grep -q 'etm rc=0' $V/drive/$c.r0.log 2>/dev/null && { echo "SYNTH $c reused"; continue; }
  ( $OTRUN --mem $((MEMG + 4)) --threads 4 --dir $B/src -- bash -c "echo HOST \$(hostname); rm -rf $B/syn/$c; \
      env MEMG=$MEMG $LC HIER=1 EXTRA=v16w/$w.sv WTOP=$w bash tools/hbm_die_v15/synth_master.sh . $B/syn/$c $c $m - - && \
      MEMG=$MEMG bash tools/hbm_die_v15/synth_etm.sh . $B/syn/$c $c" > $V/drive/$c.r0.log 2>&1
    echo "SYNTH $c rc=$? $(grep -c 'etm rc=0' $V/drive/$c.r0.log) $(tail -1 $V/drive/$c.r0.log)" ) &
done
wait
python3 $W/tools/hbm_die_v15/v16_fetch.py --views $V --remote-root $B --commit $SRC_COMMIT --contract $V/hnx_contract.json "$@" \
  > $A/fetch_s6.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch_s6.log
MISS=""; for c in "$@"; do [ -f $V/synth/$c/meta.json ] || MISS="$MISS $c"; done
[ -n "$MISS" ] && { echo "S6S_SYNTH_MISSING$MISS (no stubs)"; exit 16; }
ssh ot-epyc4 "mkdir -p $B/hnx_vplan/synth" && rsync -a $V/synth/ ot-epyc4:$B/hnx_vplan/synth/ || { echo S6S_UPLOAD_FAIL; exit 17; }
echo "S6S_DONE $(date -Is) -> chain FROM=S6"
cd $W/physical/hbm_next/die && FROM=S6 bash hnx_p4_chain.sh
