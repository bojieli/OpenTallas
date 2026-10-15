#!/bin/bash
set -eu
binary=$1
out=$2
mkdir -p "$out"
for variant in score_address late_am real_so_fault; do
 case "$variant" in
 score_address) arg=+SCORE_MUT=1; expected=FAIL;;
 late_am) arg=+AM_DELAY=40; expected=FAIL;;
 real_so_fault) arg=+FAULT_MUT=1; expected=PASS;;
 esac
 "$binary" "$arg" > "$out/$variant.log" 2>&1
 grep -q "^$expected mapped_astk" "$out/$variant.log"
 # Integrity errors must not move compiler assigned slots.
 grep -q '^TRACE LMAX cycle=363 ctl_age=350' "$out/$variant.log"
 grep -q '^TRACE EP0 trigger_cycle=388 local_age=365' "$out/$variant.log"
 grep -q '^TRACE EP7 trigger_cycle=454 local_age=438' "$out/$variant.log"
 grep -q '^TRACE Z cycle=913 ctl_age=900' "$out/$variant.log"
 echo "PASS observed_$variant expected=$expected fixed_slots_preserved"
 tail -6 "$out/$variant.log"
done
