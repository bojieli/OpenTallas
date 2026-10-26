#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "$1"); M=${2:-0}; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 - "$O/files.txt" <<'PY'
from pathlib import Path
import re,sys
s=Path('rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_c_bench.sh').read_text()
f=re.search(r'F="(.*?)"\ngrep',s,re.S).group(1).replace('$U','rtl/dsrom_sys/s81_dv/unit').replace('$R/','')
f=f.split()
f=[x for x in f if x not in ['rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host_c.sv','rtl/dsrom_sys/s81_dv/unit/test/dsdv_seq_host_bw.sv']]
s=Path('rtl/dsrom_sys/s81_dv/unit/r2/dsdv_seq_host_c_r2_lp_bench.sh').read_text()
f+=re.search(r'SRCS="(.*?)"\n',s,re.S).group(1).split()
Path(sys.argv[1]).write_text('\n'.join(dict.fromkeys(f))+'\n')
PY
mapfile -t F < "$O/files.txt"
sha256sum "${F[@]}" > "$O/sources.sha256"
"$VL" --version > "$O/verilator.version"
"$VL" --binary --timing -j "${J:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-TIMESCALEMOD \
  -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10 -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D -DOT_S81_SH_S10E \
  --top-module tb_dsdv_seq_host_c_r2_lp -GMUT="$M" "${F[@]}" --Mdir "$O/obj" > "$O/build.log" 2>&1
set +e
"$O/obj/Vtb_dsdv_seq_host_c_r2_lp" > "$O/run.log" 2>&1
rc=$?
set -e
cat "$O/run.log"
if [ "$M" = 0 ] && grep -q '^LP_LOCKSTEP PASS' "$O/run.log";then echo SEQ_REGION_LANDING_PASS;exit 0;fi
if [ "$M" = 1 ] && grep -q '^LP_LOCKSTEP FAIL' "$O/run.log" && grep -q 'MISMATCH' "$O/run.log";then echo SEQ_REGION_MISSING_LANDING_CAUGHT;exit 1;fi
echo "SEQ_REGION_UNCLASSIFIED mutant=$M rc=$rc";exit 2
