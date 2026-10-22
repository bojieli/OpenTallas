#!/usr/bin/env bash
# TOKSIM-S81C/GATH: build tb_toksim_gath (observation copy of tb_dsdv_svc_rs) against the RELEASE dsdv_svc_rs /
# dsdv_svc_rs_entry protect-libs (TOKSIM-S81/SU base_d0s0: git archive 19bf4121e, DIE 0 ST 0, FG3, MUT 0) and run the
# real-fixture gather cases with +static_io=1.   Run from the lane dir gx/:  bash gath_job.sh "CASE:GAP ..."
set -uo pipefail
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version | tee out/verilator.version
echo "HOST $(hostname) start $(date)"
COMMON=(-Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 2000 -fno-inline
        --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 -Iinc -DRS_OBS -DSVCQ_ENG_FG3 -DSU_SMU_T -DMUT=0)
if [ ! -x obj/Vtb_toksim_gath ]; then
  "$VL" --binary --top-module tb_toksim_gath -Mdir obj -GDIE=0 -GST=0 -GSRAM_MACRO=0 -GMAXCYC=40000 -j 8 -DRS_PL "${COMMON[@]}" \
    pl/dsdv_svc_rs_pl.sv pl/dsdv_svc_rs_entry_pl.sv tb_toksim_gath.sv $PWD/pl/libdsdv_svc_rs_pl.a $PWD/pl/libdsdv_svc_rs_entry_pl.a \
    > out/build_tb.log 2>&1 || { tail -30 out/build_tb.log; exit 1; }
fi
sha256sum obj/Vtb_toksim_gath pl/*.a tb_toksim_gath.sv inc/* > out/sources.sha256
for CG in $1; do
  C=${CG%%:*}; G=${CG##*:}
  ( obj/Vtb_toksim_gath +dir=$PWD/cases/$C +seed=1 +static_io=1 +sel_gap=$G > out/run_${C}_g${G}.log 2>&1
    echo "$C g$G: $(grep -h '^GATH_T ' out/run_${C}_g${G}.log) | $(grep -h '^SVCRS ' out/run_${C}_g${G}.log | grep -o 'sc_errors=[0-9]*.*verdict=[A-Z]*')" ) &
done
wait
echo "HOST $(hostname) done $(date)"
