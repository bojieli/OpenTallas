#!/bin/bash
set -uo pipefail
verilator --version | grep '5.050' || exit 2
for shape in 0 1;do
 for mut in 0 1 2 3;do
  tag=s${shape}m${mut}
  verilator --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hgi_coll_ctl_v74_safe -GSHAPE=$shape -GMUT=$mut --Mdir obj$tag *.sv *.v >build$tag.log 2>&1 || { tail -30 build$tag.log;exit 3; }
  ./obj$tag/Vtb_hgi_coll_ctl_v74_safe >$tag.log 2>&1;rc=$?
  if [ $mut = 0 ];then grep -q '^COLL_VMRT PASS' $tag.log && [ $rc = 0 ] || { cat $tag.log;exit 4; };else grep -q 'COLL_VMRT FAIL' $tag.log && [ $rc != 0 ] || { cat $tag.log;exit 5; };fi
  grep COLL_VMRT $tag.log | tail -2
 done
done
