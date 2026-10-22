#!/bin/bash
set -u
mkdir run07 || exit 99
exec > >(tee run07/run.log) 2>&1
hostname;free -b;df -B1 .;iverilog -V 2>&1 | head -4
sha256sum /usr/bin/iverilog /usr/bin/vvp
status=0
run_case() {
name=$1;proj=$2;bench=$3;top=$4;expected=$5
/usr/bin/time -v iverilog -g2012 -s "$top" -o "run07/$name.vvp" validation/official_reference.v validation/init_reference.v "$proj" "$bench" >"run07/$name.build.log" 2>&1
rc=$?;if [ "$rc" != 0 ];then cat "run07/$name.build.log";status=1;return;fi
/usr/bin/time -v vvp "run07/$name.vvp" >"run07/$name.log" 2>&1
rc=$?;echo "$name exit $rc";cat "run07/$name.log"
if [ "$expected" = pass ] && [ "$rc" != 0 ];then status=1;fi
if [ "$expected" = fail ] && [ "$rc" = 0 ];then status=1;fi
}
run_case udp_init validation/udp_functional_projection.v validation/init_tb.v init_tb pass
echo "VALIDATION_EXIT $status";exit "$status"
