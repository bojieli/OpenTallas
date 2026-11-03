#!/bin/bash
# DIE-S81-51 11-03: ot_s81ph_sel_su_pipe SELOH=1 (one-hot group select) == SELOH=0, sequential equiv (yosys equiv_induct),
# plus a mutant (one select term dropped) that must FAIL.  Run from the repo root inside the ORFS image:
#   docker run --rm --memory 8g -v $PWD:/w:ro openroad/orfs:asap7lock bash /w/rtl/dsrom_sys/s81_dv/unit/bk/test/run_seloh_equiv.sh
set -u; T=$(mktemp -d); R=/w/rtl; P=$R/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv
mk() { printf "read_verilog -sv $R/hdc/ot_hdc_prefix.sv $1 $R/dsrom_sys/s81_dv/unit/bk/test/seloh_equiv_wrap.sv\nhierarchy -check\nproc; flatten; opt_clean\nrename top0 gold; rename top1 gate\nasync2sync\nequiv_make gold gate eq\nhierarchy -top eq\nequiv_simple -seq 4\nequiv_induct -seq 4\nequiv_status -assert\n" > $2; }
mk $P $T/base.ys; yosys -q $T/base.ys > $T/base.log 2>&1; b=$?
sed "s/ja < 15; ja = ja + 1) acca_s = acca_s/ja < 14; ja = ja + 1) acca_s = acca_s/" $P > $T/mut.sv; mk $T/mut.sv $T/mut.ys
yosys -q $T/mut.ys > $T/mut.log 2>&1; m=$?
sed "s/{CB{hot_r\[je\]}}/{CB{hot_r[15-je]}}/" $P > $T/mut2.sv; grep -q "hot_r\[15-je\]" $T/mut2.sv || m2=nomut
mk $T/mut2.sv $T/mut2.ys; yosys -q $T/mut2.ys > $T/mut2.log 2>&1; m2=${m2:-$?}
echo "SELOH_EQUIV base rc=$b (want 0) mutant acca rc=$m mutant res_eq rc=$m2 (want !=0)"; [ $b = 0 ] && [ $m != 0 ] && [ "$m2" != 0 ] && [ "$m2" != nomut ]
