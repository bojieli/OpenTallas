#!/bin/bash
# DIE-QC-66/CLK 11-03: NL A0 conservative form v3 (NKP=7 all depth cuts, 0 visible cycles; balanced multi-entry ck_de
# register clock <=5k sinks/entry, rr_balance.tcl), one full build + sign-off + RE-SIGN at flow-20261103-s-qc.
set -uo pipefail
N=/srv/opentallas-scratch2/claude/die-qc-66-nlcf; K=/srv/opentallas-scratch2/claude/die-qc-66-nlcf/qfd_tile_nl_a0c_a0nl14icg1r1p7c; B=/srv/opentallas-scratch2/claude/die-qc-66-cores/nl_build; TAG=flow-20261103-s-qc
echo "START $(hostname) $(date -Is) build_commit $1" >> $N/build_v3.status
bash $K/run_kit.sh $K finish 48 16; rc=$?
echo "RUN_KIT rc $rc $(date -Is)" >> $N/build_v3.status
if [ $rc = 0 ]; then
  python3 -I $B/tools_s_qc/resign.py run --kit $K --tag $TAG --repo /home/ubuntu/OpenTallas --tools $B/tools_s_qc \
    --out $K/resign_s_qc --lane DIE-QC-66/CLK --build-commit $1 > $N/resign.log 2>&1; rr=$?
  echo "RESIGN rc $rr $(date -Is)" >> $N/build_v3.status; tail -3 $N/resign.log; [ $rr = 0 ] || rc=$rr
fi
exit $rc
