#!/usr/bin/env bash
# TOKSIM-S81C/GATH: window_load HBM-latency sensitivity on the IDX svc exe (release svc_rs libs), image L0 base
for L in 100 180; do ./Vtb_svc_lower +dir=$PWD/img/base +seed=1 +lat=$L > out/run_lat${L}_s1.log 2>&1 & done
wait; grep -h "^SVCLOW" out/run_lat*_s1.log
