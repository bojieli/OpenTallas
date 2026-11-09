#!/usr/bin/env bash
# DIE-S81-85 11-09: lock-step bench ot_s81_kp4_enc OT_S81_KP4_ENC_LA vs the define-off encoder (origin/main copy).
# usage: run_kp4_enc_la_bench.sh <repo> <workdir> [verilator]
# Runs PPCYC 0/1 x seeds 1..3 (MUT 0, PIN_FAULT 1), MUT=1 / PIN_FAULT=0 / no-gap variants, and two mutants that
# must FAIL: OT_S81_KP4_ENC_LA_MUTPOW (D built from alpha^(51 j)) and RCKRF_MUT_LA_LANE (S_0 fed from lane 1).
set -u
REPO=$1; W=$2; VL=${3:-verilator}
S=$REPO/rtl/dsrom_sys/s81_link
mkdir -p "$W/src" && cd "$W" || exit 2
cp "$S"/ot_s81_kp4_enc.sv "$S"/ot_s81_kp4_common.sv "$S"/ot_s81_gf1024.svh "$S"/ot_s81_kp4_enc_mat.svh \
   "$S"/ot_s81_kp4_enc_mat_q4.svh "$S"/ot_s81_kp4_enc_la_mat.svh "$S"/ot_s81_kp4_enc_la_mat_q4.svh \
   "$S"/tb_kp4_enc_la.sv src/
# REF = a define-off ot_s81_kp4_enc.sv (default: origin/main of REPO)
{ if [ -n "${REF:-}" ]; then cat "$REF"; else git -C "$REPO" show origin/main:rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv; fi; } \
    | sed 's/^module ot_s81_kp4_enc /module ot_s81_kp4_enc_ref /' > src/ot_s81_kp4_enc_ref.sv
grep -q "module ot_s81_kp4_enc_ref" src/ot_s81_kp4_enc_ref.sv || { echo "ref rename failed"; exit 2; }
MUTPOW=1 python3 -I "$REPO/tools/s81_link/gen_kp4_enc_la.py" src > gen_mut.log || exit 2
mkdir -p regen && python3 -I "$REPO/tools/s81_link/gen_kp4_enc_la.py" "$W/regen" > gen.log || exit 2
cmp regen/ot_s81_kp4_enc_la_mat.svh src/ot_s81_kp4_enc_la_mat.svh && echo "GEN_REPRO PASS" || echo "GEN_REPRO FAIL"
build() {  # name defines...
    local n=$1; shift
    "$VL" --binary -j 32 -O3 --x-assign fast --x-initial unique -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
        -Isrc "$@" --top-module tb_kp4_enc_la -Mdir "obj_$n" src/ot_s81_kp4_common.sv src/ot_s81_kp4_enc_ref.sv \
        src/ot_s81_kp4_enc.sv src/tb_kp4_enc_la.sv > "build_$n.log" 2>&1 || { echo "BUILD FAIL $n"; tail -20 "build_$n.log"; }
}
run() {  # obj seed label
    "./obj_$1/Vtb_kp4_enc_la" +verilator+seed+"$2" > "run_$1.log" 2>&1
    { grep -m1 "^MISMATCH" "run_$1.log" | cut -c1-120; grep "^KP4_ENC_LA" "run_$1.log"; } | sed "s/^/[$3] /"
}
for P in 0 1; do
    for s in 1 2 3; do build la_p${P}_s$s -DOT_S81_KP4_ENC_LA -GPPCYC=$P -GSEED=$s; run la_p${P}_s$s $s "LA PPCYC=$P seed $s"; done
done
build la_mut1 -DOT_S81_KP4_ENC_LA -GPPCYC=1 -GMUT=1 -GSEED=4;        run la_mut1 4 "LA MUT=1"
build la_pf0 -DOT_S81_KP4_ENC_LA -GPPCYC=1 -GPIN_FAULT=0 -GSEED=5;   run la_pf0 5 "LA PIN_FAULT=0"
build la_nogap -DOT_S81_KP4_ENC_LA -GPPCYC=1 -GGAPS=0 -GSEED=6;      run la_nogap 6 "LA back-to-back no gaps"
build m_pow -DOT_S81_KP4_ENC_LA -DOT_S81_KP4_ENC_LA_MUTPOW -GPPCYC=1 -GSEED=1; run m_pow 1 "MUTANT pow 51 (expect FAIL)"
build m_lane -DOT_S81_KP4_ENC_LA -DRCKRF_MUT_LA_LANE -GPPCYC=1 -GSEED=1;       run m_lane 1 "MUTANT lane (expect FAIL)"
