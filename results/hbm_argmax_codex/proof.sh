#!/bin/bash
set -u
positive_rc=99
mutant_rc=99
r=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for v in tree tree_mut; do
 sudo docker run --rm --memory 8g -v "$r:/work" -w /work openroad/orfs:asap7lock bash -c "yosys -p 'read_verilog -sv $v.sv; proc; opt; equiv_make tree_old tree_new m; hierarchy -top m; equiv_simple; equiv_induct; equiv_status -assert'" > "$r/$v.log" 2>&1
 rc=$?
 echo "$v rc=$rc"
 if [ "$v" = tree ]; then positive_rc=$rc; else mutant_rc=$rc; fi
done

[ "$positive_rc" -eq 0 ] && [ "$mutant_rc" -ne 0 ]
