#!/bin/bash
# DIE-QC-66/CORES-NK 11-03: one full NL RE-FORM build, NKP=2 (kit nickname kq_qfd_tile_nl_a0c_a0nl14icg1r1p2),
# kit = the DIE-QC-65 nl_b3h_eco kit (a0nl14icg1b3h) with the nkp_patch_nl.py RTL, VERILOG_TOP_PARAMS + NKP 2,
# remap_homes.py graph homes, lec.py / signoff.py from flow-20261103-s-qc; then RE-SIGN at that tag (resign.py).
#   build_nl.sh BUILD_COMMIT        (run from ot-run on the kit host)
set -uo pipefail
B=/srv/opentallas-scratch2/claude/die-qc-66-cores/nl_build; KN=qfd_tile_nl_a0c_a0nl14icg1r1p2; K=$B/$KN; TAG=flow-20261103-s-qc
echo "START $(hostname) $(date -Is) build_commit $1" >> $B/build_nl.status
bash $K/run_kit.sh $K finish 48 16; rc=$?
echo "RUN_KIT rc $rc $(date -Is)" >> $B/build_nl.status
if [ $rc = 0 ]; then
  python3 -I $B/tools_s_qc/resign.py run --kit $K --tag $TAG --repo /home/ubuntu/OpenTallas --tools $B/tools_s_qc \
    --out $K/resign_s_qc --lane DIE-QC-66/CORES-NK --build-commit $1 > $B/resign.log 2>&1; rr=$?
  echo "RESIGN rc $rr $(date -Is)" >> $B/build_nl.status; tail -3 $B/resign.log; [ $rr = 0 ] || rc=$rr
fi
exit $rc
