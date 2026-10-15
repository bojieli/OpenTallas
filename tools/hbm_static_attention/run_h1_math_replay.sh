#!/bin/bash
set -euo pipefail
exe=$(realpath "$1");vectors=$(realpath "$2");out=$3;mkdir -p "$out"
"$exe" +DIR="$vectors" +MUT=0 > "$out/math.log" 2>&1
grep -q 'PASS ATT_LOCAL_CALENDAR_FULL' "$out/math.log"
echo 'PASS logicalH1 activehead0 on unchanged fullH16 arithmetic binary; nativeprefetch/SC/PVwriter composition and wholekernel calendar remain open' > "$out/gate"
