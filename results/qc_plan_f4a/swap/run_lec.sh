#!/bin/bash
# QC-PLAN-F4A narrowed-swap LEC (yosys equiv, docker orfs:asap7lock, 4 GB cap): vmr, rp1 + both address mutants (must fail)
S=$(cd $(dirname $0) && pwd); cd $S/lec
cp ../old_suffixed.sv ../new.sv ../mut_vmr.sv ../mut_rp1.sv .
for n in vmr rp1 mutvmr mutrp1; do
  docker run --rm -m 4g --cpus 2 -v $S/lec:/lec openroad/orfs:asap7lock bash -c "Y=\$(ls /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys 2>/dev/null || which yosys); \$Y -q -l /lec/lec_$n.log -s /lec/lec_$n.ys" > lec_$n.out 2>&1
  echo "$n: $(grep -E 'Found [0-9]+ .equiv|are proven|successfully|unproven' lec_$n.log | tr '\n' ' ')"
  gzip -f lec_$n.log
done
