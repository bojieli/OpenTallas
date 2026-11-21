#!/usr/bin/env bash
# FABLE-FIX-HEAD-SERDES-R3 11-21: bench of the zero-cycle per-unit syndrome copies OT_S81_KP4_SYN_SCOPY (ot_s81_kp4_dsyn:
# each RiBM unit reads its own kept copy S_u of the syndrome register instead of the one shared S_q).
# usage: run_kp4_scopy_bench.sh <repo> <workdir> [verilator]
# Full FEC gate (tb_s81_kp4 vs tools/s81_link/rs544.py vectors, exact frames + corrections):
#   defines off, the hd_serdes form (ENC_LA + ENC_PW16 + SYN_PW8) and SCOPY alone / on the hd_serdes form must PASS;
#   with SCOPY: dec MUT 2 (Forney value) and dec MUT 3 (no syndrome restart, now in the copies) must FAIL;
#   SCOPY_MUT_STALE (unit 1 reads S one cycle late) and SCOPY_MUT_BIT (bit 7 of the unit 2 copy inverted) must FAIL.
# Last line: KP4_SCOPY_BENCH PASS|FAIL.
set -u
REPO=$1; W=$2; VL=${3:-verilator}
S=$REPO/rtl/dsrom_sys/s81_link; M=$REPO/physical/asap7_memory_macros
mkdir -p "$W" && cd "$W" || exit 2
v=PASS
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
C=-DOT_S81_KP4_SYN_SCOPY
grun off PASS
grun hd PASS $D
grun scopy_only PASS $C
grun hd_scopy PASS $D $C
grun hd_scopy_dmut2 FAIL $D $C -GDMUT=2
grun hd_scopy_dmut3 FAIL $D $C -GDMUT=3
grun m_stale FAIL $D $C -DSCOPY_MUT_STALE
grun m_bit FAIL $D $C -DSCOPY_MUT_BIT
echo "KP4_SCOPY_BENCH $v"
[ $v = PASS ]
