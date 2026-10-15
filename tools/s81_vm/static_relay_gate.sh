#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
O=${1:?out};N=${2:?banks4or8};MODE=${3:-base};mkdir -p "$O"
R=rtl/dsrom_sys/s81_ph
SOURCE="$R/vm/dsfd_vm_static_relay128.sv"
if [[ $MODE == mutant ]];then
 python3 - "$SOURCE" "$O/mutant.sv" <<'PY'
import sys
s=open(sys.argv[1]).read();assert s.count('o_sd<=i_sd;')==1
open(sys.argv[2],'w').write(s.replace('o_sd<=i_sd;','o_sd<=i_sd ^ 1\'b1;'))
PY
 SOURCE="$O/mutant.sv"
fi
iverilog -g2012 -DRELAY_NB="$N" -s tb_dsfd_vm_static_relay -o "$O/sim" "$SOURCE" "$R/vm/dsfd_vm_static_relay128_b4.sv" "$R/vm/dsfd_vm_static_relay128_b8.sv" "$R/test/tb_dsfd_vm_static_relay.sv"
vvp -n "$O/sim" > "$O/run.log" 2>&1 || { cat "$O/run.log";exit 1; }
cat "$O/run.log"
grep -q 'TB_VM_RELAY PASS' "$O/run.log"
