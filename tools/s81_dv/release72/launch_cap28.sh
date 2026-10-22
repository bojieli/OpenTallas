#!/bin/bash
# STW-S81c-DIE3-C28 local waiter: cap28 VARIANT GEN (ot-run --priority die, no host pin: any host holding the lane root)
# -> gates (c28_gen_gate.py) -> stage receipt on every physical host -> ot-run physical (--mem 160, no host pin)
# -> placement clock summary (CKR displacement + dieclk group spread) -> GRT probe (probe_chain) -> classify -> lane + EVENTs
# usage: launch_cap28.sh V C24 C26
V=$1; C24=$2; C26=$3; L=/home/ubuntu/claude-takeover-20261007/lanes/STW-S81-DIE.md; D=/home/ubuntu/scratch/s81c_die/cap28
E=/home/ubuntu/scratch/s81c_die/waiter/events.log; P="- [STW-S81c-DIE3-C28"
LR=/srv/opentallas-scratch/claude/stw-s81c-cap28; G=$LR/gen-$V; T=$LR/in/tools28
PH="ot-epyc5 ot-epyc7 ot-epyc9 ot-gold1 ot-gold2 ot-pve1"; I=/home/ubuntu/ot-scratch/claude/stw-s81c-cap28
post() { ( flock 9; echo "$P $(date +%H:%M)] $*" >> $L ) 9>>$L.lock; }
ot-run --mem 60 --threads 4 --priority die --no-spill --dir $LR -- env CLK2=1 C24=$C24 C26=$C26 I=$LR/in/cap19in SRC_TAR=$LR/in/source.tar.gz CAP25_TOOLS=$LR/in/tools CAP28_TOOLS=$T bash $T/pin_cap28.sh $V $G > $D/gen_$V.out 2>&1 < /dev/null
GH=$(grep -o 'RAN on [^:]*' $D/gen_$V.out | tail -1 | awk '{print $3}')
[ -n "$GH" ] || { post "cap28 $V GEN NOT RUN: $(tail -1 $D/gen_$V.out | cut -c1-200)"; echo "EVENT cap28${V}_genfail $(date -Is)" >> $E; exit 1; }
st=$(ssh -n -o ControlPath=none $GH "cat $G/run.exit 2>/dev/null; grep -h 'CASE_RC\|BIND_RC' $G/steps.log 2>/dev/null; tail -1 $G/case_gen.log 2>/dev/null | cut -c1-300")
if ! echo "$st" | grep -q "CASE_RC 0"; then post "cap28 $V GEN FAILED: $(echo $st | tr '\n' ' ' | cut -c1-500) ($GH:$G)"; echo "EVENT cap28${V}_genfail $(date -Is)" >> $E; exit 1; fi
gate=$(ssh -n -o ControlPath=none $GH "python3 -I $T/c28_gen_gate.py $G $T/ref26_$V.json; echo GATE_RC \$?")
dl=$(ssh -n -o ControlPath=none $GH "grep -h 'DIECLK_SPLIT\|DIECLK_CKR_RESERVE' $G/case_gen.log | cut -c1-300")
if ! echo "$gate" | grep -q "GATE_RC 0"; then post "cap28 $V GEN GATE FAIL ($GH:$G): $(echo "$gate" | head -1 | cut -c1-900)"; echo "EVENT cap28${V}_gatefail $(date -Is)" >> $E; exit 1; fi
ssh -n -o ControlPath=none $GH "cd $G && tar -czf /tmp/cap28_${V}_receipt.tar.gz bind/bind case" || exit 1
scp -q -o ControlPath=none $GH:/tmp/cap28_${V}_receipt.tar.gz $D/ || exit 1
OK=""; for h in $PH; do ssh -n -o ControlPath=none $h "mkdir -p $I && rm -f $I/cap28_${V}_rundir" && scp -q -o ControlPath=none $D/cap28_${V}_receipt.tar.gz $D/physical_cap28.sh $h:$I/ && OK="$OK,$h"; done; OK=${OK#,}
post "cap28 $V GEN PASS ($GH:$G): $(echo "$gate" | head -1 | cut -c1-1000) || $(echo $dl | cut -c1-500); physical submitted ot-run --mem 160 --priority die (no pin; hosts with the receipt $OK)"
echo "EVENT cap28${V}_gen $(date -Is)" >> $E
ot-run --mem 160 --threads 16 --priority die --no-spill --disk 60 --hosts $OK --dir /srv/opentallas-scratch/claude -- bash $I/physical_cap28.sh $V > $D/phys_$V.out 2>&1 < /dev/null &
PP=$!
RD=""; for k in $(seq 1 1440); do RD=$(for h in ${OK//,/ }; do ssh -n -o ControlPath=none $h "cat $I/cap28_${V}_rundir 2>/dev/null"; done | tail -1); [ -n "$RD" ] && break; kill -0 $PP 2>/dev/null || break; sleep 120; done
if [ -n "$RD" ]; then
  post "cap28 $V physical ADMITTED $RD (ot-run waiter PID $PP)"
  (cd /home/ubuntu/scratch/s81c_die/grtprobe && setsid -f bash ./probe_chain.sh cap28$V ${RD%%:*} ${RD#*:} > pc_cap28$V.log 2>&1 < /dev/null)
  # placement clock summary: CKR displacement + dieclk group spread, once the die clock build is done
  ( H=${RD%%:*}; R=${RD#*:}; scp -q -o ControlPath=none $D/c28_clk_summ.py $H:/tmp/c28_clk_summ.py
    for k in $(seq 1 360); do
      s=$(ssh -n -o ControlPath=none $H "grep -q DIE_CLOCK_BUILD_DONE $R/case/out/dieclk.log 2>/dev/null && echo done; test -e $R/case/run_all.done && echo ended" 2>/dev/null)
      echo "$s" | grep -q done && break; echo "$s" | grep -q ended && break; sleep 300; done
    S=$(ssh -n -o ControlPath=none $H "python3 -I /tmp/c28_clk_summ.py $R/case/out 2>&1")
    { ( flock 9; echo "$P $(date +%H:%M)] cap28 $V CLOCK AT PLACEMENT ($RD, dieclk iters ${DIECLK_ITERS:-6}; cap24 MAIN it5 ref: CKR mean 266 / max 1431 um, 593 on obstacle; groups > 80: 3, long trees 68 in 42 groups):"; echo "$S" | sed 's/^/  /' ) 9>>$L.lock; } >> $L 2>/dev/null
    echo "EVENT cap28${V}_clk $(date -Is)" >> $E ) > $D/clk_$V.log 2>&1 &
fi
wait $PP; rc=$?
python3 -I /home/ubuntu/scratch/s81c_die/die_sta_classify.py "$RD" --out $D/cls_$V > $D/cls_$V.out 2>&1 < /dev/null
post "cap28 $V physical TERMINAL rc=$rc run $RD -> $D/cls_$V.out: $(grep -m3 '^run_all\|^GRT\|fclk audit' $D/cls_$V.out | cut -c1-200 | tr '\n' ' ')"
echo "EVENT cap28$V $(date -Is)" >> $E
wait
