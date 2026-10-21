#!/bin/bash
# Q-CTLM benches (Verilator): ABI (MUT 0 PASS; 4..8 FAIL), calendar (MUT 0 PASS; 1, 2, 3 FAIL), and with --nsl12 the
# twelve-slice SETID enumeration (MUT 0 PASS; 3 FAIL).  usage: run_tt_ctlm_dv.sh [WORK] [--nsl12]
# CTLM_ONLY=abi<m>|cal<m> (S-QWCOL 10-18, closure-loop benches): run only that one; the verdict line is printed either way.
set -u
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); W=${1:-/tmp/qctlm_bench}; mkdir -p "$W"; rc=0
abi() {
    local m=$1 o=$W/abi_m$1
    [ -x $o/Vtb ] || verilator --cc --exe --build -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT \
        --x-assign 0 --x-initial 0 --top-module tb_qfd_tt_ctlm_dv_abi --prefix Vtb -GMUT=$m -Mdir $o $D/main2.cpp \
        $(sed "s#^#$R/#" $D/tt_ctlm_dv_sources.f) $D/tb_qfd_tt_ctlm_dv_abi.sv > $o.build.log 2>&1
    $o/Vtb | grep -E "CTLM_ABI_(PASS|FAIL)"
}
for m in 0 4 5 6 7 8; do [ -n "${CTLM_ONLY:-}" ] && [ "$CTLM_ONLY" != abi$m ] && continue; L=$(abi $m); echo "$L"
    if [ $m = 0 ]; then case "$L" in *PASS*) ;; *) rc=1;; esac; else case "$L" in *FAIL*) ;; *) rc=1;; esac; fi; done
for m in 0 1 2 3; do [ -n "${CTLM_ONLY:-}" ] && [ "$CTLM_ONLY" != cal$m ] && continue; L=$(python3 $D/tt_ctlm_cal_bench.py --mut $m --work $W/cal | head -1); echo "$L"
    if [ $m = 0 ]; then case "$L" in *PASS*) ;; *) rc=1;; esac; else case "$L" in *FAIL*) ;; *) rc=1;; esac; fi; done
if [ "${2:-}" = "--nsl12" ]; then
    for m in 0 3; do L=$(python3 $D/tt_ctlm_cal_bench.py --mut $m --nsl 12 --work $W/cal | head -1); echo "$L"
        if [ $m = 0 ]; then case "$L" in *PASS*) ;; *) rc=1;; esac; else case "$L" in *FAIL*) ;; *) rc=1;; esac; fi; done
fi
[ $rc = 0 ] && echo "QCTLM BENCHES: PASS" || echo "QCTLM BENCHES: FAIL"
exit $rc
