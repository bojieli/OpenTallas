#!/bin/bash
# REFILL-1725/HBMREG: run every leg of legs.tsv from the staged source root (cwd), Verilator 5.050 first on PATH.
# Each leg: RUN/<name>.log; verdict line in RUN/TABLE.tsv: name expect rc regex_hit OK|UNEXPECTED
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
P=${P:-12}; RUN=$(realpath -m ${RUN:-run}); mkdir -p $RUN; verilator --version > $RUN/verilator.txt
one() {
  IFS=$'\t' read -r name expect rx cmd <<< "$1"
  [ "$rx" = NONE ] && rx=""
  c=${cmd//RUN\//$RUN/}
  ( timeout 6h bash -c "$c" ) > $RUN/$name.log 2>&1; rc=$?
  hit=0; [ -n "$rx" ] && grep -qE "$rx" $RUN/$name.log && hit=1
  if [ $expect = pass ]; then ok=$([ $rc = 0 ] && [ $hit = 1 ] && echo OK || echo UNEXPECTED)
  # expect fail = closure_loop expected_fail_seen: with a fail regex the log decides (rc ignored); without: rc!=0 or ^FAIL
  elif [ -n "$rx" ]; then ok=$([ $hit = 1 ] && echo OK || echo UNEXPECTED)
  else ok=$({ [ $rc != 0 ] || grep -qE '^FAIL' $RUN/$name.log; } && echo OK || echo UNEXPECTED); fi
  printf '%s\t%s\trc=%s\tregex=%s\t%s\n' "$name" "$expect" "$rc" "$hit" "$ok" >> $RUN/TABLE.tsv
}
export -f one; export RUN
: > $RUN/TABLE.tsv
tr '\n' '\0' < ${LEGS:-legs.tsv} | xargs -0 -P $P -I{} bash -c 'one "$@"' _ {}
sort -o $RUN/TABLE.tsv $RUN/TABLE.tsv; cat $RUN/TABLE.tsv
n=$(wc -l < $RUN/TABLE.tsv); u=$(grep -c UNEXPECTED $RUN/TABLE.tsv)
echo "HBMREG_SUMMARY legs=$n unexpected=$u"; [ $u = 0 ]
