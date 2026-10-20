#!/bin/bash
# HBM-IDX6 unit synth + actual-Liberty native32 census (ORFS asap7 docker, TT RVT; keep-regs: (* keep *) copies kept as
# physical/common_flow/ot_keep_regs.tcl does).  usage: synth_census.sh SRCDIR TOP OUTDIR FILE...
set -uo pipefail
S=$(realpath $1); TOP=$2; O=$(realpath -m $3); shift 3; mkdir -p $O; T=$(dirname $(readlink -f $0))
FILES=""; for f in "$@"; do FILES="$FILES /s/$f"; done
rm -f $O/rl.ys; docker run --rm -u $(id -u):$(id -g) -v $S:/s:ro -v $T:/t:ro -v $O:/o openroad/orfs:asap7lock bash -c "
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; Y=\$(ls /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys 2>/dev/null || which yosys)
LIBS=''; LA=''; for f in \$L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_TT_nldm_*.lib*; do case \$f in *.gz) zcat \$f > /o/\$(basename \$f .gz);; *) cp \$f /o/;; esac; LIBS=\"\$LIBS -liberty /o/\$(basename \$f .gz)\"; LA=\"\$LA --liberty /o/\$(basename \$f .gz)\"; echo \"read_liberty -lib /o/\$(basename \$f .gz)\" >> /o/rl.ys; done
M=/s/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1_tt.lib
LA=\"\$LA --liberty \$M\"
echo \"read_liberty -lib \$M\" >> /o/rl.ys
cat > /o/s.ys <<YS
script /o/rl.ys
read_verilog -sv -DSYNTHESIS $FILES
hierarchy -check -top $TOP
proc
select -set ot_kw w:* a:keep %i
select -set ot_kc @ot_kw %ci1 t:\\\$*dff* t:\\\$*dlatch* %u %i
techmap @ot_kc
select -set ot_kc @ot_kw %ci1 t:\\\$*dff* t:\\\$*dlatch* t:\\\$_*DFF* t:\\\$_*LATCH* %u %u %u %i
setattr -set keep 1 @ot_kc
select -clear
synth -top $TOP
flatten
opt_clean -purge
dfflibmap \$LIBS
abc \$LIBS
opt_clean -purge
hilomap -singleton -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L
write_verilog -noattr /o/mapped.v
tee -o /o/stat.json stat -json \$LIBS
stat \$LIBS
YS
\$Y -q -l /o/yosys.log /o/s.ys >/dev/null 2>&1 || { tail -30 /o/yosys.log; exit 3; }
python3 /t/tools/ref_tile/native_census.py --netlist /o/mapped.v --top $TOP --out /o/census.json \$LA
sha256sum /o/*.lib /s/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1_tt.lib > /o/liberties.sha256"
