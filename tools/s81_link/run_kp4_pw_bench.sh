#!/usr/bin/env bash
# FABLE-FIX-HEAD-SD9F 11-18: bench of the zero-cycle window partial splits OT_S81_KP4_ENC_PW16 / OT_S81_KP4_SYN_PW8.
# usage: run_kp4_pw_bench.sh <repo> <workdir> [verilator]
#  1. GEN_REPRO: split_kp4_window_n.py reproduces the three committed *_w16 / *_w8 .svh files byte for byte.
#  2. encoder lock-step (tb_kp4_enc_la, PPCYC 0, same cycle): DUT with PW16 (with and without OT_S81_KP4_ENC_LA) against a
#     TRUE define-off copy (the ref file is compiled last and undefines the encoder defines for itself); seeds 1..3,
#     MUT=1, PIN_FAULT=0, no gaps.  Mutant RCKRF_MUT_PW16 (partial 5 dropped) must FAIL.
#  3. full FEC gate (tb_s81_kp4 vs tools/s81_link/rs544.py vectors) with ENC_LA + ENC_PW16 + SYN_PW8: base must PASS, enc
#     MUT 1 / dec MUT 2 must FAIL, and the split mutants RCKRF_MUT_SPW8 / RCKRF_MUT_PW16 must FAIL.
# Last line: KP4_PW_BENCH PASS|FAIL.
set -u
REPO=$1; W=$2; VL=${3:-verilator}
S=$REPO/rtl/dsrom_sys/s81_link; M=$REPO/physical/asap7_memory_macros
mkdir -p "$W/src" "$W/regen" && cd "$W" || exit 2
v=PASS
T=$REPO/tools/s81_link/split_kp4_window_n.py
python3 -I "$T" enc 16 "$S/ot_s81_kp4_enc_la_mat.svh" regen/ot_s81_kp4_enc_la_mat_w16.svh > gen.log || v=FAIL
python3 -I "$T" enc 16 "$S/ot_s81_kp4_enc_mat.svh" regen/ot_s81_kp4_enc_mat_w16.svh >> gen.log || v=FAIL
python3 -I "$T" syn 8 "$S/ot_s81_kp4_syn_mat.svh" regen/ot_s81_kp4_syn_mat_w8.svh >> gen.log || v=FAIL
for f in ot_s81_kp4_enc_la_mat_w16.svh ot_s81_kp4_enc_mat_w16.svh ot_s81_kp4_syn_mat_w8.svh; do
    if cmp -s "regen/$f" "$S/$f"; then echo "GEN_REPRO PASS $f"; else echo "GEN_REPRO FAIL $f"; v=FAIL; fi
done
cp "$S"/ot_s81_kp4_enc.sv "$S"/ot_s81_kp4_common.sv "$S"/ot_s81_gf1024.svh "$S"/ot_s81_kp4_enc_mat*.svh "$S"/ot_s81_kp4_enc_la_mat*.svh \
   "$S"/tb_kp4_enc_la.sv src/
{ printf '`undef OT_S81_KP4_ENC_LA\n`undef OT_S81_KP4_ENC_PW16\n`undef RCKRF_MUT_PW16\n'
  sed 's/^module ot_s81_kp4_enc /module ot_s81_kp4_enc_ref /' "$S/ot_s81_kp4_enc.sv"; } > src/ot_s81_kp4_enc_ref.sv
grep -q "module ot_s81_kp4_enc_ref" src/ot_s81_kp4_enc_ref.sv || { echo "ref rename failed"; exit 2; }
ebuild() {  # name defines...
    local n=$1; shift
    "$VL" --binary -j 16 -O3 --x-assign fast --x-initial unique -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
        -Isrc "$@" --top-module tb_kp4_enc_la -Mdir "obj_$n" src/ot_s81_kp4_common.sv src/ot_s81_kp4_enc.sv src/tb_kp4_enc_la.sv \
        src/ot_s81_kp4_enc_ref.sv > "build_$n.log" 2>&1 || { echo "BUILD FAIL $n"; tail -20 "build_$n.log"; v=FAIL; }
}
erun() {  # obj seed label want
    "./obj_$1/Vtb_kp4_enc_la" +verilator+seed+"$2" > "run_$1.log" 2>&1
    local l; l=$(grep "^KP4_ENC_LA" "run_$1.log" | tail -1)
    echo "[$3] ${l:-NO RESULT LINE}"
    case "$l" in "KP4_ENC_LA $4 "*) ;; *) echo "  UNEXPECTED (want $4)"; v=FAIL;; esac
}
for s in 1 2 3; do
    ebuild pwla_s$s -DOT_S81_KP4_ENC_LA -DOT_S81_KP4_ENC_PW16 -GPPCYC=0 -GSEED=$s; erun pwla_s$s $s "ENC LA+PW16 seed $s" PASS
done
ebuild pw_s1 -DOT_S81_KP4_ENC_PW16 -GPPCYC=0 -GSEED=1;                              erun pw_s1 1 "ENC PW16 (no LA) seed 1" PASS
ebuild pwla_mut1 -DOT_S81_KP4_ENC_LA -DOT_S81_KP4_ENC_PW16 -GPPCYC=0 -GMUT=1 -GSEED=4;       erun pwla_mut1 4 "ENC LA+PW16 MUT=1" PASS
ebuild pwla_pf0 -DOT_S81_KP4_ENC_LA -DOT_S81_KP4_ENC_PW16 -GPPCYC=0 -GPIN_FAULT=0 -GSEED=5;  erun pwla_pf0 5 "ENC LA+PW16 PIN_FAULT=0" PASS
ebuild pwla_nogap -DOT_S81_KP4_ENC_LA -DOT_S81_KP4_ENC_PW16 -GPPCYC=0 -GGAPS=0 -GSEED=6;     erun pwla_nogap 6 "ENC LA+PW16 no gaps" PASS
ebuild off_s1 -GPPCYC=0 -GSEED=1;                                                   erun off_s1 1 "ENC defines off (self)" PASS
ebuild m_pw -DOT_S81_KP4_ENC_LA -DOT_S81_KP4_ENC_PW16 -DRCKRF_MUT_PW16 -GPPCYC=0 -GSEED=1;   erun m_pw 1 "MUTANT partial 5 dropped (expect FAIL)" FAIL
# ---- full FEC gate
python3 "$REPO/tools/s81_link/rs544.py" selftest > ref_selftest.log 2>&1 || { echo "reference selftest FAIL"; v=FAIL; }
python3 "$REPO/tools/s81_link/rs544.py" vectors vec.hex --n 16 --seed 5 > /dev/null
F="$S/ot_s81_kp4_common.sv $S/ot_s81_kp4_enc.sv $S/ot_s81_kp4_bm.sv $S/ot_s81_kp4_dsyn.sv $S/ot_s81_kp4_ddly.sv $S/ot_s81_kp4_dchn.sv $S/ot_s81_kp4_dout.sv $S/ot_s81_kp4_dec.sv $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v $S/tb_s81_kp4.sv"
grun() {  # label want defines...
    local l=$1 want=$2; shift 2
    "$VL" --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$S --top-module tb_s81_kp4 "$@" \
        --Mdir "g_$l" -o tb $F > "gbuild_$l.log" 2>&1 || { echo "GATE BUILD FAIL $l"; tail -8 "gbuild_$l.log"; v=FAIL; return; }
    "./g_$l/tb" +vec=vec.hex +verilator+seed+11 > "grun_$l.log" 2>&1
    local r; r=$(grep TB_S81_KP4 "grun_$l.log" | tail -1)
    echo "[gate $l] ${r:-NO RESULT LINE}"
    case "$r" in *" $want") ;; *) echo "  UNEXPECTED (want $want)"; v=FAIL;; esac
}
D="-DOT_S81_KP4_ENC_LA -DOT_S81_KP4_ENC_PW16 -DOT_S81_KP4_SYN_PW8"
grun off PASS
grun pw PASS $D
grun pw_syn_only PASS -DOT_S81_KP4_SYN_PW8
grun pw_emut FAIL $D -GEMUT=1
grun pw_dmut FAIL $D -GDMUT=2
grun m_spw8 FAIL $D -DRCKRF_MUT_SPW8
grun m_pw16 FAIL $D -DRCKRF_MUT_PW16
echo "KP4_PW_BENCH $v"
[ $v = PASS ]
