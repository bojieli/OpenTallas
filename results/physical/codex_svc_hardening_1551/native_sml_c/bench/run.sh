#!/bin/bash
# S81-RCK-8 SML form C miter (verilator). Usage: run.sh <bench dir with rtl/ tb.sv files.txt>
set -u; M=$1; cd $M
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $V ] || V=/home/ubuntu/.local/opentallas-tools/bin/verilator; [ -x $V ] || V=verilator
SRCS=$(sed "s#^#$M/#" files.txt | tr '\n' ' ')
$V --binary --timing -O2 -Wno-fatal -Wno-WIDTH --top-module tb -Mdir obj -j 8 $SRCS tb.sv > build.log 2>&1 || { echo BUILD_FAIL; tail -20 build.log; exit 8; }
timeout 900 ./obj/Vtb > run.log 2>&1; rc=$?; echo "rc $rc"; grep -E 'SML_C' run.log
python3 -I - "$M" $rc <<'PY'
import sys,json,re,pathlib
m=pathlib.Path(sys.argv[1]);rc=int(sys.argv[2]);s=(m/'run.log').read_text()
ok=rc==0 and 'SML_C_MITER PASS' in s
(m/'bench_result.json').write_text(json.dumps(dict(status='PASS' if ok else 'FAIL',rc=rc,log=s[-2000:]),indent=1)+'\n')
PY
