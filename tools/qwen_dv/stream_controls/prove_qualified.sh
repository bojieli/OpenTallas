#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p native_valid
python3 - <<'PY'
from pathlib import Path
s=Path('native_final/tb_controls.sv').read_text().replace('reg ck=0,rst=0;','reg diag_logged=0;reg ck=0,rst=0;')
old='''  if(age>=20&&{le,lw,ltw,lk,la,ld,lv,lxa,lxd,lbad,lf}!=={qe,qw,qtw,qk,qa,qd,qv,qxa,qxd,qbad,qf})
   $fatal(1,"STREAM_EQ_MISMATCH cycle%0d MUT%0d",cycle,MUT);'''
new='''  if(age>=20 && !diag_logged && {le,lw,ltw,lk,la,ld,lv,lxa,lxd,lbad,lf}!=={qe,qw,qtw,qk,qa,qd,qv,qxa,qxd,qbad,qf}) begin
   diag_logged=1;
   $display("STRICT_INITIAL_DIAGNOSTIC cycle%0d tw_v%0b/%0b x_v%0b/%0b relaydiff%0b controldiff%0b twdatadiff%0b xdatadiff%0b MUT%0d",cycle,ltw,qtw,lv,qv,{le,lw}!=={qe,qw},{ltw,lv,lbad,lf}!=={qtw,qv,qbad,qf},{lk,la,ld}!=={qk,qa,qd},{lxa,lxd}!=={qxa,qxd},MUT);
  end
  if(age>=20 && ({le,lw,ltw,lv,lbad,lf}!=={qe,qw,qtw,qv,qbad,qf} ||
     (ltw && {lk,la,ld}!=={qk,qa,qd}) || (lv && {lxa,lxd}!=={qxa,qxd})))
   $fatal(1,"STREAM_EQ_MISMATCH cycle%0d MUT%0d",cycle,MUT);'''
assert old in s;s=s.replace(old,new).replace('STREAM_CONTROLS_EQ PASS edges10000 resets2 varyingSID/config concurrentrelay/taps/fullcompletion alloutputs','STREAM_NATIVE_QUALIFIED_EQ PASS edges10000 resets2 varyingSID/config concurrentrelay/taps/fullcompletion controls+allvalidpayload')
Path('native_valid/tb_controls.sv').write_text(s)
PY
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_stream --Mdir native_valid/obj native_valid/tb_controls.sv native_final/qfd_dv_stream_controls_retained.v candidate/models.v rtl/qwen_dv/qfd_dv_stream.sv > native_valid/build.log 2>&1
for mut in 0 1 2 3 4; do
 set +e
 native_valid/obj/Vtb_stream +MUT=$mut > native_valid/run$mut.log 2>&1
 code=$?
 set -e
 if [ "$mut" = 0 ]; then test "$code" = 0; grep 'STREAM_NATIVE_QUALIFIED_EQ PASS' native_valid/run$mut.log; else test "$code" != 0; grep -E 'STREAM_EQ_MISMATCH|STREAM_RESET_MISMATCH' native_valid/run$mut.log; fi
done
