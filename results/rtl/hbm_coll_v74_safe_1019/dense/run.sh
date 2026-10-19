#!/bin/bash
set -uo pipefail
verilator --version | grep '5.050' || exit 2
for shape in 0 1;do
 tag=s$shape
 verilator --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hgi_coll_ctl_v74_safe -GSHAPE=$shape -GMUT=0 -GDENSE=1 --Mdir obj$tag *.sv *.v >build$tag.log 2>&1 || { tail -30 build$tag.log;exit 3; }
 ./obj$tag/Vtb_hgi_coll_ctl_v74_safe >$tag.log 2>&1;rc=$?
 grep -q '^COLL_VMRT PASS.*pairs8192' $tag.log && [ $rc = 0 ] || { cat $tag.log;exit 4; }
 grep COLL_VMRT $tag.log
done
