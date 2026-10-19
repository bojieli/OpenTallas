#!/bin/bash
# diag.sh: build-memory diagnosis (cwd = staged repo root)
set -u; O=out_diag; mkdir -p $O
[ -f $O/g/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/g --reps 1 --only argmax_merge,a_allgather > $O/gen.txt 2>&1
( J=4 bash tools/xdie_s81/run_xdie_s81.sh $O ucie $O/g ep -GFORCE_UCIE=1 > $O/ucie.txt 2>&1; echo "EXIT $?" >> $O/ucie.txt; grep -E "Maximum resident|Elapsed" $O/ucie/time_build.log >> $O/ucie.txt ) &
( mkdir -p $O/pl; /usr/bin/time -v -o $O/pl/time.log bash rtl/dsrom_sys/s81_link/run_pdie_link_gate.sh . $O/pl/g > $O/pl.txt 2>&1; echo "EXIT $?" >> $O/pl.txt; grep -E "Maximum resident|Elapsed" $O/pl/time.log >> $O/pl.txt ) &
wait; touch $O/DONE
