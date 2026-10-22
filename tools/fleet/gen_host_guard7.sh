#!/bin/bash
# HBMc/CHAIN 10-22: GEN-host guard. ot-run --dir $B qualifies every host where $B exists; after S6/S9 synth staging the
# fleet hosts hold $B/src_* only, so GEN (S7 case_b / S10 case) was placed on ot-gold1 and died exit 127 (Codex r18 02:25).
# On every new FETCHED line (end of S6/S9 synth) hide $B on all hosts except $HOST (mv -> $B.hbmc_hold, unmarked copies only);
# on STEP S8 / STEP S9 / chain end, restore. v2: on FETCHED also overlays results/arch/hbm_release_r16_1021 (git archive HEAD of W) into ep5 $B/src: the S6/S9 src staging omits the r16 plan dir, so S7/S10 GEN died FileNotFoundError grants_d4g.json (r18 03:19). Usage: gen_host_guard2.sh NAME LOG B PID W
N=$1; L=$2; B=$3; W=$4; OVC=${5:-}
# v6 (STEWARD 09:30): NEVER a PID argument -- the controller PID is read from $(dirname L)/chain.pid and must be a live
# bash running chain_*.sh (two slips 10-22: B and a setsid wrapper PID were passed; the guard exited and unhid B).
P=$(cat "$(dirname "$L")/chain.pid" 2>/dev/null)
CMD=$(tr '\0' ' ' < /proc/${P:-0}/cmdline 2>/dev/null)
case "$CMD" in bash*chain_*.sh*) ;; *) echo "$(date -Is) $N GUARD_REFUSED: chain.pid '$P' is not a live bash chain_*.sh ('$CMD')" >&2; echo "$(date -Is) $N GUARD_REFUSED pid=$P"; exit 2;; esac
echo "$(date -Is) $N GUARD_V7 controller $P ($CMD) OVC=$OVC"
# v3: OVC = commit whose die_case_v16.py is overlaid into ep5 $B/src at every FETCHED (GEN reset fix). v4 (06:50): HOST/HOSTS were inside the v3 comment (empty!) and FETCH rc must be 0
HOST=ot-epyc5; HOSTS="ot-epyc7 ot-epyc9 ot-gold1 ot-gold2 ot-pve1 ot-agidock128"
hide() { for h in $HOSTS; do timeout 60 ssh -o ControlPath=none -o ConnectTimeout=15 $h "if [ -d $B ] && [ ! -e $(dirname $B)/.ot-run-spill-copy ] && [ ! -e $B.hbmc_hold ]; then mv $B $B.hbmc_hold && echo HID; fi" 2>&1 | sed "s/^/$N $h /"; done; }
unhide() { for h in $HOSTS; do timeout 60 ssh -o ControlPath=none -o ConnectTimeout=15 $h "if [ -d $B.hbmc_hold ] && [ ! -e $B ]; then mv $B.hbmc_hold $B && echo RESTORED; fi" 2>&1 | sed "s/^/$N $h /"; done; }
plan() { git -C $W archive HEAD results/arch/hbm_release_r16_1021 | timeout 300 ssh -o ControlPath=none $HOST "cd \$(readlink -f $B/src) && tar -x && test -f results/arch/hbm_release_r16_1021/planM/grants_d4g.json -o -f results/arch/hbm_release_r16_1021/plansM/grants_d4g.json && echo PLAN_OVERLAY_OK \$(pwd)" 2>&1 | sed "s/^/$N /"; }
TFS="tools/hbm_die_v15/die_case_v16.py tools/hbm_die_v15/die_case.py tools/die_repeaters/die_repeaters.tcl"
tool() { [ -n "$OVC" ] || return 0; for TF in $TFS; do git -C /home/ubuntu/OpenTallas show $OVC:$TF | timeout 120 ssh -o ControlPath=none $HOST "f=\$(readlink -f $B/src)/$TF; rm -f \$f && cat > \$f && echo $TF \$(grep -c 'GEN_RESET_OPEN_CHECK\|GEN_OPEN_INPUT_CHECK\|mouth_free\|ot_die_rep_carved' \$f)" 2>&1 | sed "s/^/$N TOOL_OVERLAY /"; done; echo "GEN_TOOL_OVERLAY OVC=$OVC $(for TF in $TFS; do echo -n "$(basename $TF)=$(git -C /home/ubuntu/OpenTallas show $OVC:$TF | sha256sum | cut -c1-16) "; done)remote=$(ssh -o ControlPath=none $HOST "cd \$(readlink -f $B/src) && sha256sum $TFS | cut -c1-16 | tr '\n' ' '") $(date -Is) (HBMc/CHAIN guard v6)" >> $L; }   # v6: + die_repeaters.tcl (carved channels free in the spread, d9d8095f3); overlay shas recorded in chain.log
n0=$(wc -l < $L)
while kill -0 $P 2>/dev/null; do
  n=$(wc -l < $L)
  if [ $n -gt $n0 ]; then
    new=$(sed -n "$((n0+1)),${n}p" $L); n0=$n
    echo "$new" | grep -q '^FETCHED' && { echo "$(date -Is) $N HIDE+PLAN+TOOL"; hide; plan; tool; }
    echo "$new" | grep -q -E '^STEP S(8|9) ' && { echo "$(date -Is) $N UNHIDE"; unhide; }
  fi
  t=$((t+1)); [ $((t % 20)) -eq 0 ] && /home/ubuntu/scratch/hbmc-r18e-1021/syn_partial_sweep.sh $B 2>&1 | sed "s/^/$(date -Is) $N /"   # v4: every 5 min move stale partial syn dirs (fetch picks them)
  sleep 15
done
# v7 (STEWARD 10-22 16:20): on controller exit a held copy holding only src*/syn staging (partial; all syn cells are fetched
# into $A) is DELETED, not restored: a restored unmarked partial lane root qualifies as a real --dir host and a later
# un-pinned ot-run of the lane runs GEN there with no inputs (exit 127). Anything else is restored as before.
dropstale() { for h in $HOSTS; do timeout 120 ssh -o ControlPath=none -o ConnectTimeout=15 $h "H=$B.hbmc_hold; [ -d \$H ] || exit 0; o=\$(ls -A \$H | grep -vE '^(src|src_[0-9a-f]+|syn)\$'); if [ -z \"\$o\" ]; then rm -rf \$H && echo DROPPED_PARTIAL; fi" 2>&1 | sed "s/^/$N $h /"; done; }
echo "$(date -Is) $N controller gone -> DROP partial copies, UNHIDE the rest"; dropstale; unhide
