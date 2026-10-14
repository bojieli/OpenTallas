#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p $out
if [[ -e $out/source.sha256 ]];then echo refuse_overwriting_receipt;exit 2;fi
sha256sum ot_hbm_b2_vm8_sm_sink.sv tb_hbm_b2_vm8_sm_sink*.sv >$out/source.sha256
for kind in default pipe;do
 top=tb_hbm_b2_vm8_sm_sink
 if [[ $kind == pipe ]];then top=tb_hbm_b2_vm8_sm_sink_pipe;fi
 for mut in 0 1 2 3;do
  if [[ $kind == default && $mut -gt 1 ]];then continue;fi
  case_id=$kind-mut$mut
  iverilog -g2012 -s $top -P$top.MUT=$mut -o $out/$case_id.out ot_hbm_b2_vm8_sm_sink.sv $top.sv >$out/$case_id.build.log 2>&1
  set +e
  /usr/bin/time -v vvp $out/$case_id.out >$out/$case_id.run.log 2>&1
  rc=$?
  set -e
  echo $rc >$out/$case_id.rc
  head -2 $out/$case_id.run.log
  if [[ $mut == 0 ]];then test $rc -eq 0;else test $rc -ne 0;grep -q FATAL $out/$case_id.run.log;fi
 done
done
