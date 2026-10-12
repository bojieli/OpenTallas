#!/usr/bin/env bash
# tput-map-1011 F2: CP.FETCH production-shape bench.  usage: run_cp_fetch.sh <out> [BURST] [MUT] [FLAT] [FAST]
# DS AR 1M G25 rank-0 token image (tools/tput_map_1011/cp_fetch_vectors.py) through ot_hgi_loader_cp + ot_hgi_cp_die
# (tb_hgi_cp_die_seq, iverilog: the bench's handshake tasks are iverilog-ordered; under Verilator 5.050 the cfg load fails).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); O=$(realpath -m "$1"); BURST=${2:-1}; MUT=${3:-0}; FLAT=${4:-160}; FAST=${5:-1}
mkdir -p "$O/vec"; cd "$ROOT"; G=rtl/hbm_accel/generic
[ -f "$O/vec/manifest.json" ] || python3 tools/tput_map_1011/cp_fetch_vectors.py --out "$O/vec" > "$O/vectors.log"
iverilog -g2012 ${CPF_DEFS:-} -o "$O/b${BURST}_m${MUT}.vvp" -s tb_hgi_cp_die_seq -Ptb_hgi_cp_die_seq.BURST=$BURST -Ptb_hgi_cp_die_seq.MUT=$MUT \
  -I"$O/vec" -I$G/tb -I$G -y $G -y $G/loader -y $G/peers -y $G/vm -y $G/collective -y $G/adapters -y $G/idx -Y .sv \
  $G/ot_hgi_cfg.sv $G/tb/tb_hgi_cp_die_seq.sv
cd "$O/vec" && vvp "$O/b${BURST}_m${MUT}.vvp" +FAST=$FAST +FLAT=$FLAT > "$O/run_b${BURST}_m${MUT}_f${FLAT}_fast${FAST}.log" 2>&1 || true
grep -E "CPFETCH|HGI_SEQ_DIE|FATAL|CPF_PROF" "$O/run_b${BURST}_m${MUT}_f${FLAT}_fast${FAST}.log" | head -40
