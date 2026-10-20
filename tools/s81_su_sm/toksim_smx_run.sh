#!/usr/bin/env bash
# TOKSIM-S81B/SMX: run the tb_toksim_smx exes (built by job_smx.sh, release 19bf4121e) on the golden + stress cases
S=/srv/opentallas-scratch/claude/toksim-s81b-smx; O=$S/out
rm -rf $S/cases && tar xf $S/cases.tar -C $S || exit 1
echo "HOST $(hostname) $(date)"; ls -la $O/obj_*/Vtb_toksim_smx
for n in flat16 smt16 flat2; do [ -x $O/obj_$n/Vtb_toksim_smx ] || { echo "NO EXE $n"; continue; }
  for d in $S/cases/*/; do c=$(basename $d)
    ( $O/obj_$n/Vtb_toksim_smx +case=${d%/} > $O/run_${n}_$c.log 2>&1; echo "EXIT $?" >> $O/run_${n}_$c.log ) &
  done; done
wait
for f in $O/run_*.log; do echo "== $(basename $f)"; grep -E "^SMX|MISMATCH" $f | head -8; done
