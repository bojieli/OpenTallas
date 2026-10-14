#!/usr/bin/env bash
set -eu
sha256sum -c source.sha256 > source_verify.log
for bench_case in rate blocked reset_epochs mut mut2 data_mut epoch_mut reset_mut;do
 if bash physical/qwen_romio_slots/bench_proxy_txcap_h2.sh out/$bench_case $bench_case;then result=0;else result=$?;fi
 case $bench_case in rate|blocked|reset_epochs)expected=0;;*)expected=1;;esac
 test "$result" = "$expected"
 if test "$expected" = 1;then grep -q '^FAIL qfd_link_adp512' out/$bench_case/$bench_case.log;fi
done
