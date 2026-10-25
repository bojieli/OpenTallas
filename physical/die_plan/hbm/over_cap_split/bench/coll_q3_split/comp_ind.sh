#!/bin/bash
# comp_ind.sh TAG P : compile the Verilator objects of obj_TAG one .cpp per cc1plus (the 48 vm_classes amalgamations
# needed >13 GB per unit), P in parallel, then archive + link obj_TAG/sim (PATH-HBM/Q3 10-25)
T=$1; P=${2:-32}; cd /srv/opentallas-scratch2/claude/path-hbm/q3split/obj_$T || exit 2
VI=$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include
CF="-O0 -I. -I$VI -I$VI/vltstd -DVERILATOR=1 -DVM_COVERAGE=0 -DVM_SC=0 -DVM_TIMING=1 -DVM_TRACE=0 -DVM_TRACE_FST=0 -DVM_TRACE_VCD=0 -DVM_TRACE_SAIF=0 -DVM_VPI=0 -faligned-new -fcf-protection=none -w -fcoroutines"
export CF
[ -f Vtb__pch.h.fast.gch ] || g++ $CF -x c++-header Vtb__pch.h -o Vtb__pch.h.fast.gch
[ -f Vtb__pch.h.slow.gch ] || cp Vtb__pch.h.fast.gch Vtb__pch.h.slow.gch
mkdir -p ind
ls *.cpp | grep -v "^Vtb_vm_classes_" | sed "s/\.cpp$//" | sort -u > ind/list
echo "units $(wc -l < ind/list)"
xargs -a ind/list -P $P -I{} sh -c "[ -s ind/{}.o ] || g++ \$CF -include Vtb__pch.h.fast -c {}.cpp -o ind/{}.o || echo FAILED {}" > ind/compile.log 2>&1
grep -c FAILED ind/compile.log && exit 3
for o in verilated verilated_timing verilated_threads; do [ -f $o.o ] || g++ $CF -c $VI/$o.cpp -o $o.o; done
rm -f Vtb__ALL.a; ls ind/*.o | xargs ar -rc Vtb__ALL.a && ar -s Vtb__ALL.a
g++ verilated.o verilated_timing.o verilated_threads.o Vtb__ALL.a -pthread -lpthread -latomic -o sim; echo "link rc=$?"; ls -la sim
