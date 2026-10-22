#!/usr/bin/env bash
# runs every KV-BOOTAGE bench + mutant; one summary line each
cd "$(dirname "$0")/src"
R=${1:-../runs}; mkdir -p $R
run(){ local exp=$1; shift; local out; out=$(bash tools/qwen_kv_die/kv_bootage_bench.sh "$R" "$@" 2>&1 | grep -E '^KVBA_|MISMATCH|ERROR|PHASE_C|NEG|FAULT MIS|%Error' | head -8); echo "[$exp] $* :: $(echo "$out" | tr '\n' ' ' | cut -c1-400)"; }
run pass vport 0 D=0 R=8
run pass vport 0 D=0 R=16
run pass vport 0 D=3 R=17
run pass vport 0 D=15 R=31
run fail vport 6 D=0 R=16
run fail vport 7 D=3 R=17
run fail vport 8 D=0 R=16
run pass pvctl 0 A=95
run pass pvctl 0 A=108
run fail pvctl 1 A=108
run fail pvctl 2 A=108
run pass attn 0 PL=0 FD=1 FMUT=0
run pass attn 0 PL=37 FD=49 FMUT=0
run fail attn 4 PL=37 FD=49 FMUT=0
run fail attn 5 PL=37 FD=49 FMUT=0
run fail attn 0 PL=37 FD=49 FMUT=6
run fail attn 0 PL=37 FD=49 FMUT=7
run pass calgen 0 Q=28 R=76 F=1
run pass calgen 0 Q=57 R=87 F=49
run fail calgen 6 Q=57 R=87 F=49
run fail calgen 7 Q=57 R=87 F=49
run pass dcfg 0
run fail dcfg 6
run fail dcfg 7
