#!/bin/bash
# TOK-DS-2: resume the terminated V1b hier build (376/397 masters done; make reuses finished blocks), then the V1c top (same obj, skip-identical)
set -u
R=/srv/opentallas-scratch2/claude/tok-ds-2; O=$R/build_v1b; L=$R/build_v1c; mkdir -p $L
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
echo "RESUME_START $(date -Is)" >> $L/status
/usr/bin/time -v make -C $O/obj -f Vtb_s81_die_hier.mk hier_verilation -j${J:-8} > $L/resume.log 2> $L/resume.err
rc=$?; echo "RESUME_HIER_RC $rc $(date -Is) masters $(ls -d $O/obj/V*/ | wc -l)" >> $L/status; [ $rc = 0 ] || exit $rc
J=${J:-8} $R/build_v1c.sh || exit $?
B=$R/bin_v1c/Vtb_s81_die W=$R/chk $R/run_v1c.sh
