#!/bin/bash
# MU-QW-B1 benches (2026-10-19; FLEET only, Verilator 5.050 = the closure daemon's): op-granular 4-user playback through
# qfd_tt_ctlm_dv NU 4 OPSEG 1 (leaf qfd_sys_face_mu_dhuser OPSEG + qfd_dv_cmd_cal_mu explicit range), mu_opcal frames.
#   usage: run_mu_opseg.sh WORK [part ...]     parts (default all): pass mut old
#   pass  mu_opseg_bench.py mut 0, cases red (F16 x 2 layers, 3 frames) ctx_part neg_drift neg_coll neg_ctx full (F16 x 36 layers, 1 frame
#         + 30k edges of frame 1): MU_OPSEG_PASS
#   mut   21 .. 29, 32 each MU_OPSEG_FAIL (21 / 23 / 24 / 25 / 27 / 28 / 32 on red, 22 on neg_coll, 26 on neg_drift, 29 on neg_ctx)
#   emb   MU-OPCAL-EMB (10-19) C7 witnesses on red, mut 0 RTL: --emb-t 16 (pre-fix image) and --res-skew 1 (result one
#         edge late) each MU_OPSEG_FAIL on C7
#   full2 the steady-state rate run: full, frames 0-1 + 30k edges of frame 2 (measured frame-1 rate): MU_OPSEG_PASS
#   landed (MU-DQ-CTLMKIT) the landed cluster in lockstep (TB_LANDED): LMUT 0 PASS (red, full), LMUT 1 / 2 FAIL
#   old   the OPSEG 0 benches stay PASS: run_mu_ctlm.sh (mu ctlm prog eq seq lp) + mu_tok smoke
#   dhuser  the existing R3 leaf bench (results/rtl/mu_qwen_1018/adopt_slice/tb_dhuser.sv, OPSEG 0, leaf file ALONE as
#           before): MUT 0 seeds 7 / 11 / +slip PASS, MUT 1 / 3 / 2+slip FAIL
set -u
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); W=${1:?WORK}; shift; mkdir -p "$W"; W=$(cd "$W" && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export PATH=$(dirname "$VL"):$PATH VERILATOR=$VL
verilator --version
P=${*:-pass mut old}; rc=0
want() { case " $P " in *" $1 "*) return 0;; esac; return 1; }
chk() { local ok=0; case "$3" in *$2*) ok=1;; esac
    [ $ok = 1 ] && echo "OK   $1: $3" || { echo "BAD  $1 (want $2): $3"; rc=1; }; }
if want pass; then
    python3 -I "$D/mu_opseg_bench.py" --work "$W/opseg" --mut 0 --verilator "$VL" --jobs 8 > "$W/opseg_m0.out" 2>&1
    chk opseg_m0 MU_OPSEG_PASS "$(grep -m1 '^MU_OPSEG_' "$W/opseg_m0.out")"
fi
if want mut; then
    for mc in "21 red" "22 neg_coll" "23 red" "24 red" "25 red" "26 neg_drift" "27 red" "28 red" "29 neg_ctx" "32 red"; do
        set -- $mc
        python3 -I "$D/mu_opseg_bench.py" --work "$W/opseg" --mut $1 --cases $2 --verilator "$VL" --jobs 8 > "$W/opseg_m$1.out" 2>&1
        chk opseg_m$1 MU_OPSEG_FAIL "$(grep -m1 '^MU_OPSEG_' "$W/opseg_m$1.out")"
    done
fi
if want d2duser; then
    # MU-DQ-D2DUSER (10-19): C8 user carrier on native_pos[17:16] -- mut 0 red PASS, mut 32 (user not carried) red FAIL
    python3 -I "$D/mu_opseg_bench.py" --work "$W/opseg" --mut 0 --cases red --verilator "$VL" --jobs 8 > "$W/opseg_d2du_m0.out" 2>&1
    chk d2du_m0 MU_OPSEG_PASS "$(grep -m1 '^MU_OPSEG_' "$W/opseg_d2du_m0.out")"
    python3 -I "$D/mu_opseg_bench.py" --work "$W/opseg" --mut 32 --cases red --verilator "$VL" --jobs 8 > "$W/opseg_d2du_m32.out" 2>&1
    L=$(grep -m1 '^MU_OPSEG_' "$W/opseg_d2du_m32.out"); case "$L" in *C8*) chk d2du_m32 MU_OPSEG_FAIL "$L";; *) chk d2du_m32 "MU_OPSEG_FAIL (C8)" "${L:-NO_RESULT}";; esac
fi
if want emb; then
    for wc in "emb16 --emb-t 16" "skew1 --res-skew 1"; do
        set -- $wc; t=$1; shift
        python3 -I "$D/mu_opseg_bench.py" --work "$W/opseg" --mut 0 --cases red --tag _$t "$@" --verilator "$VL" --jobs 8 > "$W/opseg_$t.out" 2>&1
        L=$(grep -m1 '^MU_OPSEG_' "$W/opseg_$t.out"); case "$L" in *C7*) chk opseg_$t MU_OPSEG_FAIL "$L";; *) chk opseg_$t "MU_OPSEG_FAIL (C7)" "${L:-NO_RESULT}";; esac
    done
fi
if want full2; then
    python3 -I "$D/mu_opseg_bench.py" --work "$W/opseg" --mut 0 --cases full --full-frames 2 --tag _full2 --verilator "$VL" --jobs 8 > "$W/opseg_full2.out" 2>&1
    chk opseg_full2 MU_OPSEG_PASS "$(grep -m1 '^MU_OPSEG_' "$W/opseg_full2.out")"
fi
if want landed; then
    # MU-DQ-CTLMKIT 10-19: the landed cluster qfd_tt_ctlm_dv_lpf_lp (NU 4 / OPSEG 1 re-cut) in lockstep with the NU 4
    # OPSEG 1 dut on the compiled op-segment frames (TB_LANDED): LMUT 0 PASS on red + full; LMUT 1 / 2 FAIL on red
    for lc in "0 red full" "1 red" "2 red"; do
        set -- $lc; lm=$1; shift
        python3 -I "$D/mu_opseg_bench.py" --work "$W/opseg_l" --mut 0 --cases "$@" --landed $lm --tag _l$lm --verilator "$VL" --jobs 8 > "$W/opseg_l$lm.out" 2>&1
        L=$(grep -m1 '^LANDED_LOCKSTEP' "$W/opseg_l$lm.out" | cut -c1-200)
        [ $lm = 0 ] && chk landed_l$lm "LANDED_LOCKSTEP PASS" "${L:-NO_RESULT}" || chk landed_l$lm "LANDED_LOCKSTEP FAIL" "${L:-NO_RESULT}"
        [ $lm = 0 ] && chk landed_l${lm}_mu MU_OPSEG_PASS "$(grep -m1 '^MU_OPSEG_' "$W/opseg_l$lm.out")"
    done
fi
if want old; then
    bash "$D/run_mu_ctlm.sh" "$W/old_ctlm" > "$W/old_ctlm.out" 2>&1
    chk old_ctlm "MU_CTLM BENCHES: PASS" "$(tail -1 "$W/old_ctlm.out")"
    bash "$R/rtl/test/mu_qwen_tok/run_mu_tok_smoke.sh" "$W/old_tok" > "$W/old_tok.out" 2>&1
    chk old_tok "PASS" "$(tail -1 "$W/old_tok.out")"
fi
if want dhuser; then
    H=$R/results/rtl/mu_qwen_1018/adopt_slice
    for c in "pass_s7 0 7 -" "pass_s11 0 11 -" "slip_pass 0 7 +slip" "mut1 1 7 -" "mut3 3 7 -" "mut2_slip 2 7 +slip"; do
        set -- $c; pa=$4; [ "$pa" = - ] && pa=
        verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_dhuser -GMUT=$2 -GSEED=$3 \
            -Mdir "$W/dhuser_$1" -o sim "$R/rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv" "$H/tb_dhuser.sv" > "$W/dhuser_$1.build.log" 2>&1
        "$W/dhuser_$1/sim" $pa > "$W/dhuser_$1.out" 2>&1
        L=$(grep -m1 "TB_DHUSER" "$W/dhuser_$1.out")
        case $1 in pass*|slip_pass) chk dhuser_$1 "TB_DHUSER PASS" "${L:-NO_RESULT}";; *) chk dhuser_$1 "TB_DHUSER FAIL" "${L:-NO_RESULT}";; esac
    done
fi
[ $rc = 0 ] && echo "MU_OPSEG BENCHES: PASS" || echo "MU_OPSEG BENCHES: FAIL"
exit $rc
