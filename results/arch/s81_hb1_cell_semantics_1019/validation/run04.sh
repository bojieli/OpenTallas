#!/bin/bash
set -u
mkdir run04 || exit 99
exec > >(tee run04/run.log) 2>&1
hostname;free -b;df -B1 .;iverilog -V 2>&1 | head -4
sha256sum /usr/bin/iverilog /usr/bin/vvp
status=0
run_case() {
name=$1;proj=$2;bench=$3;top=$4;expected=$5
/usr/bin/time -v iverilog -g2012 -s "$top" -o "run04/$name.vvp" validation/official_reference.v "$proj" "$bench" >"run04/$name.build.log" 2>&1
rc=$?;if [ "$rc" != 0 ];then cat "run04/$name.build.log";status=1;return;fi
/usr/bin/time -v vvp "run04/$name.vvp" >"run04/$name.log" 2>&1
rc=$?;echo "$name exit $rc";cat "run04/$name.log"
if [ "$expected" = pass ] && [ "$rc" != 0 ];then status=1;fi
if [ "$expected" = fail ] && [ "$rc" = 0 ];then status=1;fi
}
run_case binary functional_projection.v validation/tb.v tb fail
run_case fourstate functional_projection.v validation/tb_fourstate.v tb fail
run_case udp_binary validation/udp_functional_projection.v validation/tb.v tb pass
run_case udp_fourstate validation/udp_functional_projection.v validation/tb_fourstate.v tb pass
run_case udp_init validation/udp_functional_projection.v validation/init_tb.v init_tb pass
run_case mut_polarity validation/udp_mut_polarity.v validation/tb.v tb fail
run_case mut_priority validation/udp_mut_priority.v validation/tb.v tb fail
run_case mut_comb validation/udp_mut_comb.v validation/tb.v tb fail
echo "VALIDATION_EXIT $status";exit "$status"
