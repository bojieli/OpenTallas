#!/bin/bash
set -u
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
for k in old good mutant;do
 cp /work/fixture.sv /work/$k.sv
 if [ "$k" = mutant ];then sed -i 's/hard u(/hard #(.UNDECLARED(1)) u(/' /work/$k.sv;fi
 echo "read_slang --keep-hierarchy --top top /work/$k.sv --blackboxed-module hard" > /work/$k.ys
 echo "write_rtlil /work/$k.il" >> /work/$k.ys
 if [ "$k" != old ];then echo 'setparam -unset gf t:hard' >> /work/$k.ys; echo 'setparam -unset ADD_LAT t:hard' >> /work/$k.ys; echo 'setparam -unset ZW t:hard' >> /work/$k.ys;fi
 echo 'read_verilog -overwrite /work/stub.v' >> /work/$k.ys
 echo 'hierarchy -check -top top' >> /work/$k.ys
 $Y -s /work/$k.ys > /work/$k.log 2>&1
 echo "$k=$?"
done
