#!/usr/bin/env bash
# run_eq.sh REPO OUT [CYC]: per-column composition == gold d34578d6f + declared shift; SMUT 1..9 must FAIL. iverilog, fleet only.
set -u; cd "${1:?}"; OUT=${2:?}; CYC=${3:-48000}; mkdir -p "$OUT/gold"; rc=0
s=rtl/hbm_accel/generic/adapters/static_su/programme; P=results/die_hbm_1103/reform/split_p8; GC=${GOLD_COMMIT:-d34578d6f}
for f in rtl/lib/ot_rst_relay.sv $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv; do git show "$GC:$f" > "$OUT/gold/$(basename $f)" || exit 2; done
python3 - "$OUT/gold" <<'PY'
import re,sys,glob
d=sys.argv[1]; fs=sorted(glob.glob(d+'/*.sv')); txt={f:open(f).read() for f in fs}
mods=set(m for t in txt.values() for m in re.findall(r'^\s*module\s+(\w+)',t,re.M))
pat=re.compile(r'\b('+'|'.join(sorted(mods,key=len,reverse=True))+r')\b')
for f,t in txt.items(): open(f,'w').write(pat.sub(lambda m:'gold_'+m.group(1),t))
PY
SRAM=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
FW=physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py; F="rtl/lib/ot_rst_relay.sv $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv $s/ot_hbm_su_programme_pcol.sv"
python3 $FW --top ot_hbm_su_pcol_s --out $OUT/s_fs.sv --pass-param MUT --pass-param PMUT $F || exit 3
python3 $FW --top ot_hbm_su_pcol_l --out $OUT/l_fs.sv --pass-param MUT --pass-param PMUT $F || exit 3
python3 $FW --top ot_hbm_su_pcol_h --out $OUT/h_fs.sv --pass-param HMUT $F || exit 3
FR=$(grep -l "module ot_hbm_face_reg" -r physical/die_plan/hbm/over_cap_split/reform_1103 physical/die_plan/hbm_arch_cores 2>/dev/null | head -1)
[ -n "$FR" ] && case "$FR" in *.sv|*.v) FRS=$FR;; *) FRS=;; esac
if [ -z "${FRS:-}" ]; then cat > $OUT/face_reg.sv <<'V'
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
FRS=$OUT/face_reg.sv; fi
iverilog -g2012 -o $OUT/sim -s tb_pslice_pcol -Ptb_pslice_pcol.CYC=$CYC $OUT/gold/*.sv $F $OUT/s_fs.sv $OUT/l_fs.sv $OUT/h_fs.sv $FRS $P/ot_hbm_su_programme_pslice_c5__p8fs.sv $SRAM $P/tb_pslice_pcol.sv > $OUT/build.log 2>&1 || { tail -5 $OUT/build.log; exit 4; }
for m in 0 1 2 3 4 5 6 7 8 9; do
  [ $m = 9 ] && continue
  iverilog -g2012 -o $OUT/sim$m -s tb_pslice_pcol -Ptb_pslice_pcol.CYC=$CYC -Ptb_pslice_pcol.SMUT=$m $OUT/gold/*.sv $F $OUT/s_fs.sv $OUT/l_fs.sv $OUT/h_fs.sv $FRS $P/ot_hbm_su_programme_pslice_c5__p8fs.sv $SRAM $P/tb_pslice_pcol.sv >> $OUT/build.log 2>&1
  ( vvp -n $OUT/sim$m > $OUT/run$m.log 2>&1 ) &
done; wait
for m in 0 1 2 3 4 5 6 7 8; do g=$(grep -h 'PCOL_EQ ' $OUT/run$m.log | tail -1); e=FAIL; [ $m = 0 ] && e=PASS; echo "SMUT $m expect $e: $g"; [ "$(echo $g | cut -d' ' -f2)" = "$e" ] || rc=1; done; echo EQ_EXIT $rc; exit $rc
