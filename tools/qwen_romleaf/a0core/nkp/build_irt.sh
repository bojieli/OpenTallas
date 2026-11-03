#!/bin/bash
# DIE-QC-66/CORES-NK 11-03: one full NK build, NKP=7 + ICG_IDLE_RT=1 (kit nickname kq_qfd_tile_nk_a0c_a0nk14icg1ir1p7r),
# kit = the DIE-QC-65 nk_ireg kit (a0nk14icg1ir1) with the patched RTL, NKP 7 + ICG_IDLE_RT 1 params, remapped graph homes
# (remap_homes.py + homes_irt.py) and signoff.py / lec.py from flow-20261103-s-qc; then RE-SIGN at that tag (resign.py).
#   build_irt.sh BUILD_COMMIT        (run from ot-run on the kit host)
set -uo pipefail
B=/srv/opentallas-scratch2/claude/die-qc-66-cores/nk_build; KN=qfd_tile_nk_a0c_a0nk14icg1ir1p7r; K=$B/$KN; TAG=flow-20261103-s-qc
echo "START $(hostname) $(date -Is) build_commit $1" >> $B/build_irt.status
bash $K/run_kit.sh $K finish 48 16; rc=$?
echo "RUN_KIT rc $rc $(date -Is)" >> $B/build_irt.status
if [ $rc = 0 ]; then
  python3 -I $B/tools_s_qc/resign.py run --kit $K --tag $TAG --repo /home/ubuntu/OpenTallas --tools $B/tools_s_qc \
    --out $K/resign_s_qc --lane DIE-QC-66/CORES-NK --build-commit $1 > $B/resign.log 2>&1; rr=$?
  echo "RESIGN rc $rr $(date -Is)" >> $B/build_irt.status; tail -3 $B/resign.log; [ $rr = 0 ] || rc=$rr
fi
exit $rc
