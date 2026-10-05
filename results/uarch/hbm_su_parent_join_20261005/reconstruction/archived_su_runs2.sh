#!/bin/bash
cd /srv/opentallas-scratch/claude/hbm-fmax-su/src
O=/srv/opentallas-scratch/claude/hbm-fmax-su/out/su; W=/srv/opentallas-scratch/claude/hbm-fmax-su/work_su; A=/srv/opentallas-scratch/admit.sh
export OT_VFLAGS="--unroll-count 4 -fno-dfg"
T="python3 -u tools/su_fmax_measure.py su-run --f12 --out $O --work $W"
($A 12 -- $T --bcast 7 --ret 8 --mlat 6 --alat 5 --n 1024 --m 256 --fp dpi_beh --cases su_cases_v2.pkl > $O/b7r8m6a5_N1024_v2.log 2>&1; OT_REUSE_BUILD=1 $A 12 -- $T --bcast 7 --ret 8 --mlat 6 --alat 5 --n 1024 --m 256 --fp dpi_beh --cases su_cases_p6om.pkl > $O/b7r8m6a5_N1024_p6om.log 2>&1) &
$A 24 -- $T --bcast 7 --ret 8 --mlat 6 --alat 5 --n 64 --m 16 --fp rtl --cases su_cases_v2.pkl > $O/b7r8m6a5_N64_rtlf12_v2.log 2>&1 &
$A 12 -- $T --bcast 7 --ret 8 --mlat 6 --alat 5 --n 64 --m 16 --fp dpi_beh --cases su_cases_v2.pkl > $O/b7r8m6a5_N64_dpibeh_v2.log 2>&1 &
wait
