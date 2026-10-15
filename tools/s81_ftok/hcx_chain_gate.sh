#!/bin/bash
# hcx_chain_gate.sh <src root> <out> <vec root> <image dir> <post image dir> [LAYER] [modes]
# tb_s81_hcx_chain: the real HC coefficient chain (4-rank projection + gatherpack + post) under the actual fixed issuer.
# Modes: cal (measure offsets; params from CALX), base (HLAYOUT 1 h_rows layout: PASS), canon (HLAYOUT 0 on canonical rows:
# PASS = component layout), mut_layout (HLAYOUT 0 on h_rows: FAIL), mut_post (MUT_POST 1: FAIL). Env: GP (the -G offsets of
# the compiled chain: "-GFAST=.. -GPROJ_DONE=.. -GG_OFF=.. -GPOST_TOG=.. -GPOST_SEEN=.. -GDONE_OFF=.. -GISSUE0=.. -GISSUE1=..")
set -u
SRC=$1; OUT=$2; VEC=$3; IMG=$4; PIMG=$5; LAYER=${6:-1}; MODES=${7:-"base canon mut_layout mut_post"}
VL=${VL:-verilator}; GP=${GP:-}
mkdir -p $OUT/rom; ln -sf $IMG/hcx_r*_p*_b*.viamap.hex $OUT/rom/ 2>/dev/null; ln -sf $PIMG/hcx_post_p*.viamap.hex $OUT/rom/
LD=$(printf L%02d $LAYER)
python3 $SRC/tools/s81_ftok/hcx_chain_vectors.py --src $VEC/vec/$LD --out $OUT/vec_h || exit 1
python3 $SRC/tools/s81_ftok/hcx_chain_vectors.py --src $VEC/vec/$LD --out $OUT/vec_c --canonical || exit 1
g() { echo "$GP" | tr ' ' '\n' | sed -n "s/^-G$1=//p"; }
I0=$(g ISSUE0); I0=${I0:-200}; I1=$(g ISSUE1); I1=${I1:-4400}; DO=$(g DONE_OFF); DO=${DO:-4000}
for v in vec_h vec_c; do
python3 - $SRC $OUT/$v $LAYER $I0 $I1 $DO <<'PY' || exit 1
import sys; from pathlib import Path
src,out,layer,i0,i1,do=sys.argv[1],Path(sys.argv[2]),*map(int,sys.argv[3:])
sys.path.insert(0,src+'/tools/s81_static_control')
from program import encode_program, issuer_done_row
pin_to_pin=do+1      # chain samples the command pin one edge after it rises; c_done set DONE_OFF edges later
rows=[dict(engine=9,arg=(layer<<15)|(0<<1)|0,issue=i0,done=issuer_done_row(i0,pin_to_pin),pin_to_pin=pin_to_pin),
      dict(engine=9,arg=(layer<<15)|(640<<1)|1,issue=i1,done=issuer_done_row(i1,pin_to_pin),pin_to_pin=pin_to_pin)]
rows.append(dict(engine=15,arg=0,issue=rows[-1]['done']+4,done=0))
mc=encode_program(rows,stage=0,phase=3)
(out/'program.mem').write_text(''.join(f"{w['word']:09x}\n" for w in mc['writes']))
print('program', [(r['issue'],r['done']) for r in rows])
PY
done
POSTF="rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv
 rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv rtl/hbm_accel/generic/adapters/ot_hgi_hc_record.sv rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv
 rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_wrd.sv rtl/link/ot_fifo_sram_fwft.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_vm_scheduled.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_post_native.sv
 rtl/dsrom_sys/s81_native_head_connect/ot_s81_head_gain_stream.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_post_gain_native.sv"
FILES="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_projection_leaf.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_prefetch.sv
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_controller.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_hrow_transpose.sv
 rtl/dsrom_sys/s81_hcx/dsfd_sp_hcx_projection.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_gatherpack.sv
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_chain_seq.sv rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv
 $POSTF rtl/dsrom_sys/s81_hcx/test/tb_s81_hcx_chain.sv"
( cd $SRC && sha256sum $FILES tools/s81_ftok/hcx_chain_vectors.py tools/s81_ftok/hcx_chain_gate.sh tools/s81_static_control/program.py ) > $OUT/sources.sha256
for m in $MODES; do
  case $m in cal) X="-GCAL=1";; base) X="";; canon) X="-GHLAYOUT=0";; mut_layout) X="-GHLAYOUT=0";; mut_post) X="-GMUT_POST=1";; esac
  V=vec_h; [ $m = canon ] && V=vec_c
  ( cd $SRC && $VL --binary --timing -O3 -CFLAGS -O1 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-PINMISSING \
      --top-module tb_s81_hcx_chain -GLAYER=$LAYER $GP $X --Mdir $OUT/obj_$m -j ${J:-8} $FILES > $OUT/build_$m.log 2>&1 ) \
   && $OUT/obj_$m/Vtb_s81_hcx_chain +DIR=$OUT/$V +OT_ROM_DIR=$OUT/rom > $OUT/run_$m.log 2>&1 &
done
wait
for m in $MODES; do
  v=$(grep -h "HCX_CHAIN \(PASS\|FAIL\|CAL\)" $OUT/run_$m.log 2>/dev/null | tail -1); [ -z "$v" ] && v="NO_RESULT $(grep -m1 -i '%Error' $OUT/build_$m.log)"
  exp=PASS; case $m in mut_*) exp=FAIL;; cal) exp=CAL;; esac
  echo "$m expect $exp: $v | $(grep -h '^HCX_CHAIN commands' $OUT/run_$m.log)"
done | tee $OUT/verdicts.log
if grep -q "expect CAL" $OUT/verdicts.log; then exit 0; fi
if [ $(grep -c "expect PASS: HCX_CHAIN PASS" $OUT/verdicts.log) -eq $(grep -c "expect PASS" $OUT/verdicts.log) ] && \
   [ $(grep -c "expect FAIL: HCX_CHAIN FAIL" $OUT/verdicts.log) -eq $(grep -c "expect FAIL" $OUT/verdicts.log) ]; then
  echo "HCX_CHAIN_GATE PASS" | tee -a $OUT/verdicts.log; else echo "HCX_CHAIN_GATE FAIL" | tee -a $OUT/verdicts.log; exit 1; fi
