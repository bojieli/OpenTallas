#!/bin/bash
# TOK-DS-2 V1c runs: L0 job0 host stream + job start (KS) -> check_seqhost.py vs the compiled calendar; mutant + no-KS control
set -u
R=/srv/opentallas-scratch2/claude/tok-ds-2; B=${B:-$R/bin_v1c/Vtb_s81_die}; O=${O:-$R/run_v1c}; mkdir -p $O
N=${NCYC:-11000}; T0=${HOST_T0:-16}; P=$R/l0prog/try3; W=${W:-/srv/opentallas-scratch2/claude/wt/tok-ds-2}
echo "RUN_START $(date -Is) NCYC=$N HOST_T0=$T0 B=$B" >> $O/status
cd $O
/usr/bin/time -v $B +NCYC=$N +HOSTIN=$R/v1stim/job0_s5.memh +HOSTN=2875 +HOST_T0=$T0 +HOST_AFTER_ALIVE=1 +KS=1 > base.log 2> base.time
/usr/bin/time -v $B +NCYC=$N +HOSTIN=$R/v1stim/job0_s5_mut.memh +HOSTN=2875 +HOST_T0=$T0 +HOST_AFTER_ALIVE=1 +KS=1 > mut.log 2> mut.time
/usr/bin/time -v $B +NCYC=$N +HOSTIN=$R/v1stim/job0_s5.memh +HOSTN=2875 +HOST_T0=$T0 +HOST_AFTER_ALIVE=1 > noks.log 2> noks.time
[ -d "${ROMDIR:-$R/romdir_all}" ] && /usr/bin/time -v $B +NCYC=$N +HOSTIN=$R/v1stim/job0_s5.memh +HOSTN=2875 +HOST_T0=$T0 +HOST_AFTER_ALIVE=1 +KS=1 +OT_ROM_DIR=${ROMDIR:-$R/romdir_all} > rom.log 2> rom.time
wait
for f in base mut noks rom; do [ -f $f.log ] || continue; echo "== $f $(grep -E 'Maximum resident|Elapsed' $f.time | tr -s ' ' | tr '\n' ' ')" >> $O/status; grep -E "TB_S81_DIE (SUMMARY|PASS|FAIL)|PROG (KS|FCODE|STATUS)" $f.log >> $O/status
  [ $f = noks ] || (cd $W && python3 tools/s81_dv/layer_prog/check_seqhost.py --dir $P --log $O/$f.log > $O/$f.check 2>&1; echo "CHECK_SEQHOST $f rc $?" >> $O/status; tail -3 $O/$f.check >> $O/status); done
echo "RUN_END $(date -Is)" >> $O/status
