#!/usr/bin/env bash
# HBM-CORES-REBAL-9 (runs on epyc2): after the lanes__canon m5w1 CTS kit job, post-CTS TT STA (sta_cts.tcl) + 4_cts dump +
# render (rend_cts.py) as a diagnostic probe in docker (memory capped).  Outputs in $R/canon_post/.
R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-9; K=$(ls -d $R/kits/*m5w1); O=$R/canon_post; mkdir -p $O
C=$(ls $K/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1)
[ -n "$C" ] || { echo "$(date) no 4_cts.odb; FAIL markers: $(cat $K/FAIL_* 2>/dev/null)" > $O/status; exit 1; }
cp $K/hold_gate.log $O/ 2>/dev/null
docker run --rm --name r9-canon-post-$$ --cpus=8 --memory=48g --memory-swap=48g -v $K:/work -v $R:/out -e OT_VCLK_TT=250 \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  openroad -exit /out/sta_cts.tcl > /out/canon_post/sta_cts.log 2>&1; \
  ODB=$C OUT=/out/canon_post/cts.csv openroad -python -exit /work/dump_placed.py > /out/canon_post/dump.log 2>&1; chown -R $(id -u):$(id -g) /out/canon_post"
python3 $R/rend_cts.py $O/cts.csv $O/cts.png > $O/rend.log 2>&1
echo "$(date) done: $(grep -h WNS_ALL $O/sta_cts.log) $(grep -h OT_HOLD_GATE $O/hold_gate.log | tail -1)" > $O/status
