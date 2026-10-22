#!/bin/bash
# name host root base
set -e
name=$1 host=$2 root=$3 base=$4
out=$root/pg_bind_eco_native
ssh -o ControlPath=none $host "mkdir -p $out && test ! -e $out/post_audit.json"
scp -q -o ControlPath=none /home/ubuntu/scratch/s81-native-pg/pg_bind_eco.tcl /home/ubuntu/scratch/s81-native-pg/native_pg_binding.tcl $host:$out/
exec /home/ubuntu/bin/ot-run --mem 16 --threads 1 --dir $root -- bash -c "docker run --rm --network none -v $base:/input:ro -v $out:/out openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /out/pg_bind_eco.tcl > $out/run.log 2>&1; rc=\$?; cd $out; sha256sum /dev/null >/dev/null; diff -q pre_signal.txt post_signal.txt && echo SIGNAL_IDENTICAL >> run.log || echo SIGNAL_DIFF >> run.log; sha256sum 6_final_pgbound.odb pre_signal.txt post_signal.txt >> run.log; sha256sum $base/6_final.odb >> run.log; echo RC=\$rc >> run.log; tail -12 run.log"
