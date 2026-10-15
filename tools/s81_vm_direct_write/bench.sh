#!/bin/bash
set -eu
O=${1:?output}
LEAF=${2:?capture or scatter}
CASE=${3:-base}
MODE=${4:-0}
S=rtl/dsrom_sys/s81_ph
mkdir -p "$O"
CAP="$S/vm/dsfd_vm_static_write_capture128.sv"
SCAT="$S/vm/dsfd_vm_static_scatter_b8_out.sv"
define=
if [ "$LEAF" = capture ] && [ "$CASE" = mutant ];then
 python3 - "$CAP" "$O/capture_actual_mut.sv" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text();needle='o_data<=i_data;';assert s.count(needle)==1
q=Path(sys.argv[2]);q.write_text(s.replace(needle,"o_data<=i_data^128'h1;"))
q.with_suffix('.json').write_text(json.dumps(dict(source=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mutant_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),mutation='actualcapture o_data bit0 inverted; unchangedmoduleports/clock/reset; baseline scatter untouched'),indent=2)+'\n')
PY
 CAP="$O/capture_actual_mut.sv"
elif [ "$LEAF" = scatter ] && [ "$CASE" = mutant ];then define=-DOT_VM_DIRECT_SCATTER_MUT_DATA
elif [ "$LEAF" = scatter ] && [ "$CASE" = address ];then define=-DOT_VM_DIRECT_SCATTER_MUT_ADDR
elif [ "$CASE" != base ];then echo 'unknown actualDUT mutation';exit 2
fi
iverilog -g2012 $define -s tb_dsfd_vm_static_direct_scatter -o "$O/tb" "$S/vm/dsfd_vm_static_scatter.sv" "$CAP" "$SCAT" "$S/test/tb_dsfd_vm_static_direct_scatter.sv" > "$O/build.log" 2>&1
rc=0
vvp "$O/tb" +mode="$MODE" > "$O/run.log" 2>&1 || rc=$?
cat "$O/run.log"
exit "$rc"
