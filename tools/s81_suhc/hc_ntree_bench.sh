#!/bin/bash
# S81 HC NORM tree variant (el1014-s81-norm-tree) composition gate as a closure-loop bench: the production shape of
# tools/s81_suhc/hc_gate_bench.sh (HIER 3, CNL_PIN 1, CHAIN_STEP 6, LANE_SPECIALIZE 1) at the PRODUCTION NG 256 with dsfd_sp_hc NTREE 1
# (hier/ot_s81_hc_ntree.sv), golden_L0_L2 + two stress runs against the CPU golden.  NG 64 is not a shape of the variant: its
# 20 vectors a norm exceed the two-slot partial lane (NV <= 8, ot_s81_hc_cnclt $fatal); production NG 256 has 5.
#   hc_ntree_bench.sh <out dir> <mut> [tile]   mut 0 + no tile: exact (RUN <tag> pass); mut 3, or a variant tile's
#                                              mutant (hc_gate.py TILES[...]["mut"]): RUN <tag> fail
# NT_K (bottom collectors' fire offset) is a constant of the half-octet pipeline (the far tile's leaf is the last one
# at every NG): the variant's calibrated value, overridable by env NT_K.
set -euo pipefail
out=$1; mut=${2:-0}; tile=${3:-}
NT_K=${NT_K:-67}
PKL_SHA=8c18c0655ccf6a14
for c in "${S81_SU_CASES:-}" tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl \
         /srv/opentallas-scratch2/claude/s81-suhc/su_cases_v2_ildr.pkl "$HOME/s81-suhc/su_cases_v2_ildr.pkl"; do
    [ -n "$c" ] && [ -s "$c" ] && { pkl=$c; break; }
done
[ -n "${pkl:-}" ] || { echo "hc_ntree_bench: su_cases_v2_ildr.pkl fixture not found on $(hostname)"; exit 97; }
got=$(sha256sum "$pkl" | cut -c1-${#PKL_SHA})
[ "$got" = "$PKL_SHA" ] || { echo "hc_ntree_bench: fixture $pkl sha256 $got != $PKL_SHA"; exit 97; }
[ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$out"
python3 tools/s81_suhc/hc_gate.py prep --cases "$pkl" --out "$out" --ng 256
python3 tools/s81_suhc/hc_gate.py run --out "$out" --ng 256 --hier 3 --cnl-pin 1 --chain-step 6 --lane-specialize 1 \
    --ntree 1 --nt-k "$NT_K" --mut "$mut" ${tile:+--tile-mut $tile} --tmax 30000
