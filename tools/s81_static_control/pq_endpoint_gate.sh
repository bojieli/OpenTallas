#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output dir};mkdir "$out";cd "$out"
for phw in 9 10;do
mkdir "phw$phw";cd "phw$phw"
ENDPOINT_PHW="$phw" PYTHONPATH="$root/tools/s81_static_control" python3 - <<'PY'
import os
from program import encode_program
from pq_descriptors import encode_descriptors,FIELDS
# Component image only: opaque native shape words; no production timing claim.
rows=[dict(engine=0,arg=i%4,issue=i*4,done=i*4+14)for i in range(126)]
rows += [dict(engine=14,arg=0,issue=516,done=0),dict(engine=15,arg=0,issue=520,done=0)]
image=encode_program(rows,7,0)
open('program.hex','w').write(''.join(f"{x['word']:09x}\n"for x in image['writes']))
phw=int(os.environ["ENDPOINT_PHW"])
fields=dict(ph=17 if phw==9 else 529,np=0,xbase=8192,xps=5120,obase=4096,ops=320,fmt=1,observed_end_edges=12,native_tag=0)
open('descriptor.hex','w').write(''.join(f'{x:09x}\n'for x in encode_descriptors([dict(fields,native_tag=t)for t in range(4)],phase_width=phw)))
value=0;shift=0
for k,w in [(k,phw if k=="ph" else w) for k,w in FIELDS]:value|=fields[k]<<shift;shift+=w
open('fields.hex','w').write(f'{value:023x}\n')
PY
for mut in 0 1;do
 iverilog -g2012 -DENDPOINT_MUT="$mut" -DENDPOINT_PHW="$phw" -s tb_s81_pq_command_endpoint -o gate.sim \
 "$root/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv" \
 "$root/rtl/dsrom_sys/s81_static_control/ot_s81_pq_command_endpoint.sv" \
 "$root/rtl/dsrom_sys/s81_static_control/test/tb_s81_pq_command_endpoint.sv" > "compile_$mut.log" 2>&1
 if [[ "$mut" == 0 ]];then modes='0 1 2 3 4';else modes=0;fi
 for mode in $modes;do
  if vvp gate.sim +mode="$mode" > "run_${mut}_${mode}.log" 2>&1;then rc=0;else rc=$?;fi
  echo "$rc" > "run_${mut}_${mode}.exit"
  if [[ "$mut" == 0 ]];then test "$rc" == 0;else test "$rc" != 0;grep -q 'fixed completion/tag moved' "run_${mut}_${mode}.log";fi
  cat "run_${mut}_${mode}.log"
 done
done
rm gate.sim
cd ..
done
sha256sum "$root/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_pq_command_endpoint.sv" "$root/rtl/dsrom_sys/s81_static_control/test/tb_s81_pq_command_endpoint.sv" "$root/tools/s81_static_control/pq_descriptors.py" "$root/tools/s81_static_control/pq_endpoint_gate.sh" > source.sha256
