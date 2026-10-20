#!/bin/bash
# S81-DIE7 real-view die STA tt / ff / ss + die_clock_check + classify (needs out/grt.odb)
D=$(cd $(dirname $0) && pwd); N=dvrvsta-$$; mkdir -p $D/sta
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-64}g -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/sta_tt.tcl > /work/sta/sta_tt.log 2>&1 && /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/sta_ff.tcl > /work/sta/sta_ff.log 2>&1 && /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/sta_ss.tcl > /work/sta/sta_ss.log 2>&1; chmod -R a+rwX /work/sta"
rc=$?
python3 $D/dcc/tools/die_clock_check.py report $D/sta/die_clock_dump_tt.tsv --out $D/sta/die_clock_check_tt.json --pairs $D/pairs.json > $D/sta/die_clock_check_tt.log 2>&1
python3 $D/dcc/tools/die_clock_check.py report $D/sta/die_clock_dump_ff.tsv --out $D/sta/die_clock_check_ff.json --pairs $D/pairs.json > $D/sta/die_clock_check_ff.log 2>&1
python3 $D/dcc/tools/die_clock_check.py report $D/sta/die_clock_dump_ss.tsv --out $D/sta/die_clock_check_ss.json --pairs $D/pairs.json > $D/sta/die_clock_check_ss.log 2>&1
python3 $D/classify.py $D tt ff ss > $D/sta/classes.txt 2>&1
echo $rc > $D/sta/run.exit; exit $rc
