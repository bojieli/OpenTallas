#!/bin/bash
# STW-S81d-GEN local waiter: cap31 GEN (ot-run --priority die, no host pin) -> cap30 gate (c28_gen_gate.py, relay-count deltas only)
# -> stage receipt -> PHASE pre (place + die clock, --mem 64, no pin) -> clock summary -> PHASE probe (repeaters + initial GRT,
# --mem 160, same host) -> probe summary to the lane.  The full 30-iteration GRT + STA (PHASE full) is launched by hand after the probe.
# usage: launch_cap31.sh V C24 C26   (env ROUTE_ARGS passed to the GEN route step)
V=$1; C24=$2; C26=$3; L=/home/ubuntu/claude-takeover-20261007/lanes/STW-S81-DIE.md; D=/home/ubuntu/scratch/s81c_die/cap31
E=/home/ubuntu/scratch/s81c_die/waiter/events.log; P="- [STW-S81d-GEN"
LR=/srv/opentallas-scratch/claude/stw-s81c-cap28; G=/srv/opentallas-scratch/claude/stw-s81d-cap31/gen-$V; T=$LR/in/tools31
PH="ot-epyc5 ot-epyc7 ot-epyc9 ot-gold1 ot-gold2 ot-pve1"; I=/home/ubuntu/ot-scratch/claude/stw-s81d-cap31
post() { ( flock 9; echo "$P $(date +%H:%M)] $*" >> $L ) 9>>$L.lock; }
ot-run --mem 60 --threads 4 --priority die --no-spill --dir $LR -- env CLK2=1 C24=$C24 C26=$C26 ROUTE_ARGS="${ROUTE_ARGS:-}" I=$LR/in/cap19in SRC_TAR=$LR/in/source.tar.gz CAP25_TOOLS=$LR/in/tools CAP28_TOOLS=$T bash $T/pin_cap31.sh $V $G > $D/gen_$V.out 2>&1 < /dev/null
GH=$(grep -o 'RAN on [^:]*' $D/gen_$V.out | tail -1 | awk '{print $3}')
[ -n "$GH" ] || { post "cap31 $V GEN NOT RUN: $(tail -1 $D/gen_$V.out | cut -c1-200)"; exit 1; }
st=$(ssh -n -o ControlPath=none $GH "cat $G/run.exit 2>/dev/null; grep -h 'CASE_RC\|BIND_RC' $G/steps.log 2>/dev/null; tail -1 $G/case_gen.log 2>/dev/null | cut -c1-300")
if ! echo "$st" | grep -q "CASE_RC 0"; then post "cap31 $V GEN FAILED: $(echo $st | tr '\n' ' ' | cut -c1-500) ($GH:$G)"; exit 1; fi
gate=$(ssh -n -o ControlPath=none $GH "python3 -I $T/c28_gen_gate.py $G $T/ref26_$V.json; echo GATE_RC \$?")
fl=$(ssh -n -o ControlPath=none $GH "cat $G/force_landing.log; grep -h ROUTE_DONE $G/route.log; cat $G/cap31_plan.log | cut -c1-80")
if ! echo "$gate" | grep -q "GATE_RC 0"; then post "cap31 $V GEN GATE FAIL ($GH:$G): $(echo "$gate" | head -1 | cut -c1-900) | $(echo $fl | cut -c1-200)"; exit 1; fi
ssh -n -o ControlPath=none $GH "cd $G && tar -czf /tmp/cap31_${V}_receipt.tar.gz bind/bind case" || exit 1
scp -q -o ControlPath=none $GH:/tmp/cap31_${V}_receipt.tar.gz $D/ || exit 1
OK=""; for h in $PH; do ssh -n -o ControlPath=none $h "mkdir -p $I && rm -f $I/cap31_${V}_rundir" && scp -q -o ControlPath=none $D/cap31_${V}_receipt.tar.gz $D/physical_cap31.sh $D/ctrl_corner_fix.tcl $D/c28_clk_summ.py $h:$I/ && OK="$OK,$h"; done; OK=${OK#,}
post "cap31 $V GEN PASS ($GH:$G): $(echo "$gate" | head -1 | cut -c1-700) | $(echo $fl | cut -c1-200); physical PHASE pre (place + die clock) submitted ot-run --mem 64 --priority die (no pin; $OK)"
ot-run --mem 64 --threads 16 --priority die --no-spill --disk 60 --hosts $OK --dir /srv/opentallas-scratch/claude -- env MW=600 PHASE=pre bash $I/physical_cap31.sh $V > $D/phys_pre_$V.out 2>&1 < /dev/null
rc=$?
RD=$(for h in ${OK//,/ }; do ssh -n -o ControlPath=none $h "cat $I/cap31_${V}_rundir 2>/dev/null"; done | tail -1); H=${RD%%:*}; R=${RD#*:}
S=$(ssh -n -o ControlPath=none $H "python3 -I $I/c28_clk_summ.py $R/case/out 2>&1" | head -8)
{ ( flock 9; echo "$P $(date +%H:%M)] cap31 $V PHASE pre rc=$rc ($RD); CLOCK AT PLACEMENT:"; echo "$S" | sed 's/^/  /' ) 9>>$L.lock; } >> $L 2>/dev/null
[ $rc -eq 0 ] || exit 1
ot-run --mem 160 --threads 16 --priority die --no-spill --disk 60 --hosts $H --dir /srv/opentallas-scratch/claude -- env MW=600 PHASE=probe bash $I/physical_cap31.sh $V > $D/phys_probe_$V.out 2>&1 < /dev/null
rc=$?
scp -q -o ControlPath=none /home/ubuntu/scratch/s81c_die/grtprobe/grt_probe_summ.py $H:/tmp/s81d_grt_probe_summ.py
S=$(ssh -n -o ControlPath=none $H "python3 -I /tmp/s81d_grt_probe_summ.py $R/probe0 2>&1; grep -h 'OT_DIE_REP\|OT_GRT_S' $R/case/out/run.log | cut -c1-200 | head -4")
{ ( flock 9; echo "$P $(date +%H:%M)] cap31 $V GRT PROBE (rep600, M2-M9, M6-M8 0.10, congestion_iterations 0) rc=$rc ($RD/probe0); ref cap24 rep600 probe 0.27M:"; echo "$S" | sed 's/^/  /' ) 9>>$L.lock; } >> $L 2>/dev/null
echo "EVENT cap31${V}_probe $(date -Is)" >> $E
