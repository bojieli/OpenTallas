#!/usr/bin/env bash
set -eu
export MU_RX_SRAM=1 MU_IN_PIPE=1 MU_HIER_LANES=1 J=8
for row in 'lepmu none 5' 'lepmuh none 1' 'lepmuh none 5' 'lepmu TAGDROP 1' 'lepmu LANDCUT 1' 'lepmu STALEHD 1' 'lepmu VSKEW 1' 'lepmuh HSTAMP 1' 'lepmuh KSOFF 1' 'lepmuh VSKEW 1';do
 read -r bench mutant seed <<< "$row"
 rc=0
 bash tools/s81_dv/mu_kit_bench.sh out_matrix/$bench-$mutant-$seed "$bench" "$mutant" "$seed" > "matrix-$bench-$mutant-$seed.log" 2>&1 || rc=$?
 if [ "$mutant" = none ];then test "$rc" = 0;else test "$rc" = 1;! grep -q BUILD_FAILED "matrix-$bench-$mutant-$seed.log";fi
 echo "MATRIX_CASE $row rc=$rc"
done
# Actual disabled hierarchy on the same changed source (legacy path).
MU_HIER_LANES=0 bash tools/s81_dv/mu_kit_bench.sh out_matrix/legacy lepmuh none 1 > matrix-legacy.log 2>&1
echo MATRIX_PASS
