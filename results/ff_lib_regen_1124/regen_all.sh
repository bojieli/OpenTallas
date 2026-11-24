#!/bin/bash
# run every staged regen dir that has no out_ff.lib yet, N in parallel
E=$(cd $(dirname $0) && pwd); N=${1:-8}
ls -d $E/*/ | while read d; do d=${d%/}; m=$(basename $d)
  [ -f $d/base/6_final.odb ] && [ -f $d/old_tt.lib ] && [ ! -f $d/out_ff.lib ] && echo $m; done > $E/todo.txt
echo "todo $(wc -l < $E/todo.txt)"
cat $E/todo.txt | xargs -P $N -I{} bash -c "python3 -I $E/clkpins.py $E/{}/old_tt.lib > $E/{}/clocks.txt; bash $E/regen_run.sh $E/{} {}"
