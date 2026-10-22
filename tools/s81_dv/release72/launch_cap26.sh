#!/bin/bash
# STW-S81c-DIE2-C25 local waiter: cap26 VARIANT GEN (gold2, ot-run die) -> stage receipt -> ot-run physical (own host set per
# variant: MAIN and FB never share a queue) -> GRT probe (probe_chain) -> classify -> lane + events
V=$1; C24=$2; C26=$3; PH=$4; L=/home/ubuntu/claude-takeover-20261007/lanes/STW-S81-DIE.md; D=/home/ubuntu/scratch/s81c_die/cap26; E=/home/ubuntu/scratch/s81c_die/waiter/events.log
GH=ot-gold2; GR=/srv/opentallas-scratch/claude; G=$GR/stw-s81c-cap26-$V; IN=/home/ubuntu/ot-scratch/claude/stw-s81c-cap25-in
I=/home/ubuntu/ot-scratch/claude/stw-s81c-cap26; T=$IN/tools; P="- [STW-S81c-DIE2-C25"
ot-run --mem 60 --threads 4 --priority die --hosts $GH --dir $GR -- env CLK2=1 C24=$C24 C26=$C26 I=$IN/cap19in SRC_TAR=$IN/source.tar.gz CAP25_TOOLS=$T bash $T/pin_cap26.sh $V $G > $D/gen_$V.out 2>&1 < /dev/null
st=$(ssh -n -o ControlPath=none $GH "cat $G/run.exit 2>/dev/null; grep -h 'CASE_RC\|BIND_RC' $G/steps.log 2>/dev/null; tail -1 $G/case_gen.log 2>/dev/null | cut -c1-300")
if ! echo "$st" | grep -q "CASE_RC 0"; then echo "$P $(date +%H:%M)] cap26 $V GEN FAILED: $(echo $st | tr '\n' ' ') ($GH $G)" >> $L; echo "EVENT cap26${V}_genfail $(date -Is)" >> $E; exit 1; fi
gs=$(ssh -n -o ControlPath=none $GH "grep -h 'DIE_GEN_SAFETY\|RS_CHAIN_PLACE' $G/case_gen.log | cut -c1-260; grep -h ROUTE_DONE $G/route.log; grep -h 'DIE_PORT_BIND' $G/bind.log | cut -c1-200; grep -h 'EP_ROOTS\|CAP25_TABLE' $G/cap25_table.log | cut -c1-200; grep -h CAP26_PLAN $G/cap26_plan.log | cut -c1-150")
ssh -n -o ControlPath=none $GH "cd $G && tar -czf /tmp/cap26_${V}_receipt.tar.gz bind/bind case" || exit 1
scp -q -o ControlPath=none $GH:/tmp/cap26_${V}_receipt.tar.gz $D/ || exit 1
OK=""; for h in $PH; do ssh -n -o ControlPath=none $h "mkdir -p $I" && scp -q -o ControlPath=none $D/cap26_${V}_receipt.tar.gz $D/physical_cap26.sh $h:$I/ && OK="$OK,$h"; done; OK=${OK#,}
echo "$P $(date +%H:%M)] cap26 $V GEN PASS: $(echo "$gs" | tr '\n' ' ' | cut -c1-900); physical submitted ot-run --mem 160 --priority die hosts $OK" >> $L
echo "EVENT cap26${V}_gen $(date -Is)" >> $E
ot-run --mem 160 --threads 16 --priority die --hosts $OK --dir $I -- bash $I/physical_cap26.sh $V > $D/phys_$V.out 2>&1 < /dev/null &
PP=$!
RD=""; for k in $(seq 1 720); do RD=$(for h in ${OK//,/ }; do ssh -n -o ControlPath=none $h "cat $I/cap26_${V}_rundir 2>/dev/null"; done | tail -1); [ -n "$RD" ] && break; sleep 120; done
[ -n "$RD" ] && (cd /home/ubuntu/scratch/s81c_die/grtprobe && setsid -f bash ./probe_chain.sh cap26$V ${RD%%:*} ${RD#*:} > pc_cap26$V.log 2>&1 < /dev/null)
wait $PP; rc=$?
python3 -I /home/ubuntu/scratch/s81c_die/die_sta_classify.py "$RD" --out $D/cls_$V > $D/cls_$V.out 2>&1 < /dev/null
echo "$P $(date +%H:%M)] cap26 $V physical TERMINAL rc=$rc run $RD -> $D/cls_$V.out: $(grep -m3 '^run_all\|^GRT\|fclk audit' $D/cls_$V.out | cut -c1-200 | tr '\n' ' ')" >> $L
echo "EVENT cap26$V $(date -Is)" >> $E
