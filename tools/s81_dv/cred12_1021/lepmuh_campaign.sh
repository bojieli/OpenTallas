#!/bin/bash
set -u
O=${1:?outdir}
B=lepmuh
export MU_CTRL32=1 MU_RX_SRAM=1 MU_IN_PIPE=1
export MU_EXTRA_DEFS='+define+OT_S81SL_LEP_NFACE +define+OT_S81SL_LEP_RSTHD +define+OT_S81SL_LEP_RPRLY'
rc=0
bash tools/s81_dv/cred12_1021/run.sh "$O/none_1" "$B" none 1; r=$?
if [ "$r" -ne 0 ]; then echo "CRED12_UNEXPECTED $B none seed1 rc$r"; rc=1; fi
bash tools/s81_dv/cred12_1021/run.sh "$O/none_5" "$B" none 5; r=$?
if [ "$r" -ne 0 ]; then echo "CRED12_UNEXPECTED $B none seed5 rc$r"; rc=1; fi
bash tools/s81_dv/cred12_1021/run.sh "$O/TAGDROP_1" "$B" TAGDROP 1; r=$?
if [ "$r" -ne 1 ]; then echo "CRED12_UNEXPECTED $B TAGDROP seed1 rc$r"; rc=1; fi
bash tools/s81_dv/cred12_1021/run.sh "$O/LANDCUT_1" "$B" LANDCUT 1; r=$?
if [ "$r" -ne 1 ]; then echo "CRED12_UNEXPECTED $B LANDCUT seed1 rc$r"; rc=1; fi
echo "CRED12_CAMPAIGN $B rc$rc"
exit "$rc"
