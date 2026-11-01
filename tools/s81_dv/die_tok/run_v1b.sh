#!/bin/bash
# TOK-DS-2 V1b runs: L0 job0 host stream (base), payload-bit mutant, no-host control -- same binary, in parallel
set -u
R=/srv/opentallas-scratch2/claude/tok-ds-2; B=$R/build_v1b/obj/Vtb_s81_die; O=${O:-$R/run_v1b}; mkdir -p $O
N=${NCYC:-9000}; T0=${HOST_T0:-16}
echo "RUN_START $(date -Is) NCYC=$N HOST_T0=$T0 (after alive)" >> $O/status
cd $O
/usr/bin/time -v $B +NCYC=$N +HOSTIN=$R/v1stim/job0_s5.memh +HOSTN=2875 +HOST_T0=$T0 +HOST_AFTER_ALIVE=1 > base.log 2> base.time &
/usr/bin/time -v $B +NCYC=$N +HOSTIN=$R/v1stim/job0_s5_mut.memh +HOSTN=2875 +HOST_T0=$T0 +HOST_AFTER_ALIVE=1 > mut.log 2> mut.time &
/usr/bin/time -v $B +NCYC=$N > nohost.log 2> nohost.time &
wait
for f in base mut nohost; do echo "== $f $(grep -E 'Maximum resident|Elapsed' $f.time | tr -s ' ' | tr '\n' ' ')" >> $O/status; grep -E "TB_S81_DIE (SUMMARY|PASS|FAIL)" $f.log >> $O/status; done
echo "RUN_END $(date -Is)" >> $O/status
