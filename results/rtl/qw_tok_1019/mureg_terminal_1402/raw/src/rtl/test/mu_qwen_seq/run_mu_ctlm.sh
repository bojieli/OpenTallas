#!/bin/bash
# MU-ADOPT-CTLM benches (2026-10-19; FLEET only, Verilator 5.050 = the closure daemon's): qfd_dv_cmd_cal_mu NU 4 adopted
# into qfd_tt_ctlm_dv / qfd_tt_ctlm_dv_lpf(_lp).
#   usage: run_mu_ctlm.sh WORK [part ...]     parts (default all): mu  ctlm  prog  lp  eq  seq
#   mu    rtl/test/mu_qwen_seq/mu_ctlm_bench.py: mut 0 PASS; 16 17 18 19 20 FAIL (4 users through qfd_tt_ctlm_dv)
#   ctlm  rtl/test/qwen_dv/run_tt_ctlm_dv.sh --nsl12 (existing ABI / calendar / SETID benches, NU 1: identity)
#   prog  rtl/test/qwen_dv/tt_ctlm_prog_bench.py on the committed compiled image, --hard 1 --landed 1: the NU 1 flat block
#         and the NU 4 landed cluster (dh_user 0) in lockstep: CTLM_PROG PASS + LANDED_LOCKSTEP PASS; --mut 1 FAIL
#   lp    rtl/qwen_dv/lp/qfd_tt_ctlm_dv_lpf_lp_bench.sh (regenerated, NU 4, random dh_user): audit PASS, unland FAIL, MUT 0
#         PASS, 1 / 2 FAIL (MUT 4 = late u_hr reset, not observable: HF-4 waiver, reported as INFO)
#   eq    rtl/qwen_dv/lp/tb_qfd_tt_ctlm_dv_lpf_eq.sv NU 4 random dh_user: OPSEG 0 DMUT 0 PASS, 5 / 6 FAIL; OPSEG 1 DMUT 0 PASS, 5 / 29 FAIL
#   seq   rtl/test/mu_qwen_seq/run_mu_seq.sh (qfd_dv_cmd_cal_mu, UFOLD default 0): mut 0 PASS, 4 5 11..15 FAIL
set -u
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); W=${1:?WORK}; shift; mkdir -p "$W"; W=$(cd "$W" && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export PATH=$(dirname "$VL"):$PATH VERILATOR=$VL
verilator --version
P=${*:-mu ctlm prog lp eq seq}; rc=0
want() { case " $P " in *" $1 "*) return 0;; esac; return 1; }
chk() { # name expect(PASS|FAIL) line
    local ok=0; case "$3" in *$2*) ok=1;; esac
    [ $ok = 1 ] && echo "OK   $1: $3" || { echo "BAD  $1 (want $2): $3"; rc=1; }; }
if want mu; then
    for m in 0 16 17 18 19 20; do
        python3 -I "$D/mu_ctlm_bench.py" --work "$W/mu" --mut $m --verilator "$VL" --jobs 8 > "$W/mu_m$m.out" 2>&1
        L=$(head -1 "$W/mu_m$m.out"); [ $m = 0 ] && chk mu_m$m MU_CTLM_PASS "$L" || chk mu_m$m MU_CTLM_FAIL "$L"
    done
fi
if want ctlm; then
    bash "$R/rtl/test/qwen_dv/run_tt_ctlm_dv.sh" "$W/qctlm" --nsl12 > "$W/ctlm.out" 2>&1
    chk ctlm "QCTLM BENCHES: PASS" "$(tail -1 "$W/ctlm.out")"
fi
if want prog; then
    IMG=$R/results/rtl/qwen_layer_tput_1018/ctlm_prog/image
    (cd "$R" && python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img "$IMG" --hard 1 --landed 1 --work "$W/prog") > "$W/prog_m0.out" 2>&1
    chk prog_m0 ": PASS" "$(head -1 "$W/prog_m0.out")"
    chk prog_m0_landed "LANDED_LOCKSTEP PASS" "$(grep -m1 'LANDED_LOCKSTEP' "$W/prog_m0.out")"
    (cd "$R" && python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img "$IMG" --hard 1 --mut 1 --work "$W/prog") > "$W/prog_m1.out" 2>&1
    chk prog_m1 ": FAIL" "$(head -1 "$W/prog_m1.out")"
fi
if want lp; then
    (cd "$R" && SIM=verilator bash rtl/qwen_dv/lp/qfd_tt_ctlm_dv_lpf_lp_bench.sh "$W/lp") > "$W/lp.out" 2>&1
    # MUT 4 (late u_hr reset) is not observable: HF-4 waived it in the kit spec, so judge audit + MUT 0 / 1 / 2
    chk lp_audit "AUDIT PASS" "$(grep -m1 '^AUDIT ' "$W/lp.out")"; chk lp_unland "AUDIT-UNLAND FAIL" "$(grep -m1 'AUDIT-UNLAND' "$W/lp.out")"
    chk lp_m0 "LP_LOCKSTEP PASS" "$(grep -m1 '^MUT 0:' "$W/lp.out")"
    for m in 1 2; do chk lp_m$m "LP_LOCKSTEP FAIL" "$(grep -m1 "^MUT $m:" "$W/lp.out")"; done
    echo "INFO lp_m4 (waived, not observable): $(grep -m1 '^MUT 4:' "$W/lp.out")"
fi
if want eq; then
    SRCS="$(sed "s#^#$R/#" "$R/rtl/test/qwen_dv/tt_ctlm_dv_sources.f") $R/rtl/qwen_dv/qfd_tt_ctlm_dv_lpf.sv $R/rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv"
    # MU-QW-DIE 10-19: OPSEG 0 (DMUT 0 / 5 / 6) and OPSEG 1 (DMUT 0 / 5 / 29: the landed form takes OPSEG + the context record)
    for mo in "0 0" "5 0" "6 0" "0 1" "5 1" "29 1"; do
        set -- $mo; m=$1; o=$2; t=m${m}_o${o}
        verilator --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign 0 --x-initial 0 \
            --top-module tb_qfd_tt_ctlm_dv_lpf_eq -GDMUT=$m -GNU=4 -GOPSEG=$o $SRCS "$R/rtl/qwen_dv/lp/tb_qfd_tt_ctlm_dv_lpf_eq.sv" \
            -Mdir "$W/eq$t" > "$W/eq_build$t.log" 2>&1 && "$W/eq$t/Vtb_qfd_tt_ctlm_dv_lpf_eq" > "$W/eq_$t.out" 2>&1
        L=$(grep -m1 -E 'LPF_EQ (PASS|FAIL)' "$W/eq_$t.out" 2>/dev/null)
        [ $m = 0 ] && chk eq_$t "LPF_EQ PASS" "${L:-NO_RESULT}" || chk eq_$t "LPF_EQ FAIL" "${L:-NO_RESULT}"
    done
fi
if want seq; then
    bash "$D/run_mu_seq.sh" "$W/seq" > "$W/seq.out" 2>&1
    chk seq "MU_SEQ BENCHES: PASS" "$(tail -1 "$W/seq.out")"
fi
[ $rc = 0 ] && echo "MU_CTLM BENCHES: PASS" || echo "MU_CTLM BENCHES: FAIL"
exit $rc
