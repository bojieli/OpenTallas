#!/usr/bin/env bash
set -euo pipefail
mode=${1:?pass|clock_mutant|data_mutant};out=${2:?output directory}
root=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$out";out=$(cd "$out" && pwd)
python3 - "$root" "$out" "$mode" <<'PYCODE'
from pathlib import Path
import sys
root,out,mode=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
s=(root/'rtl/dsrom_sys/s81_station_native/dsfd_hstnh_1024.sv').read_text()
if mode=='clock_mutant':
 assert s.count('.a(ck[0])')==1;s=s.replace('.a(ck[0])','.a(~ck[0])')
elif mode=='data_mutant':
 assert s.count('.i_d(di[511:0])')==1;s=s.replace('.i_d(di[511:0])',".i_d(di[511:0] ^ 512'd1)")
else: assert mode=='pass'
(out/'dut.sv').write_text(s)
PYCODE
verilator --binary --timing --top-module tb -Wno-fatal -j 2 --Mdir "$out/obj" "$root/rtl/common/ot_fwd_link_stage.sv" "$out/dut.sv" "$root/tools/s81_station_native/tb_hstnh_1024.sv" > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb" > "$out/sim.log" 2>&1
rc=$?
set -e
cat "$out/sim.log"
if [ "$mode" = pass ]; then [ "$rc" = 0 ] && grep -q 'STATION PASS 20000 words' "$out/sim.log";else [ "$rc" != 0 ] && grep -q 'STATION FAIL' "$out/sim.log" && echo "STATION MUTANT REJECTED $mode";fi
