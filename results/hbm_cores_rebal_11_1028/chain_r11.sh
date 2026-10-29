#!/usr/bin/env bash
# HBM-CORES-REBAL-11 (from REBAL-10 chain_r10.sh): collect one hand trial run: on 3_place -> placed csv + render + TT STA
# (ideal clock); on 4_cts (or run end) -> post-CTS TT STA (propagated) + render.  Diagnostic probes in docker (capped).
#   chain_r11.sh KITDIR OUTDIR OTRUN_PID
K=$1; O=$2; P=$3; R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-11; mkdir -p $O
G=$K/macro_reg_guide.json; [ -f $G ] || G=none
B() { ls $K/run/results/asap7/*/base/$1.odb 2>/dev/null | head -1; }
probe() {  # $1 stage $2 prop
  docker run --rm --name r11-$(basename $O)-$1-$$ --cpus=8 --memory=48g --memory-swap=48g -v $K:/work -v $R:/r -v $O:/out \
    -e OT_VCLK_TT=250 -e STAGE=$1 -e PROP=$2 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc \
    "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /r/bin/sta_r11.tcl > /out/sta_$1.log 2>&1; \
     ODB=$(B $1 | sed "s|$K|/work|") OUT=/out/$1.csv openroad -python -exit /work/dump_placed.py > /out/dump_$1.log 2>&1; \
     chown -R $(id -u):$(id -g) /out"
  python3 $R/bin/rend_r11.py $O/$1.csv $G $O/$1.png "$(basename $K | sed 's/.*-_//') $1" > $O/rend_$1.log 2>&1
  echo "$(date) $1 done: $(grep -h 'WNS_ALL\|NEG_END' $O/sta_$1.log | tr '\n' ' ') $(head -1 $O/rend_$1.log)" >> $O/status
}
while [ -z "$(B 3_place)" ] && kill -0 $P 2>/dev/null; do sleep 120; done
[ -n "$(B 3_place)" ] && probe 3_place 0
while kill -0 $P 2>/dev/null; do sleep 120; done
if [ -n "$(B 4_cts)" ]; then probe 4_cts 1; else echo "$(date) no 4_cts.odb; FAIL markers: $(cat $K/FAIL_* 2>/dev/null)" >> $O/status; fi
cp $K/hold_gate.log $O/ 2>/dev/null
echo "$(date) chain end" >> $O/status
