#!/bin/bash
# Per-tile qualification of the hard S81 HC leaves by the production-shape composition gate (s81hc-1013 r5; see TILES
# in tools/s81_suhc/hc_gate.py).  NG 256, HIER 3 (half-octet tiles + split column roots + chain-tail split), CNL_PIN 1,
# CHAIN_STEP 6, LANE_SPECIALIZE 1.  NOT with OT_S81_HC_PAD_HARD: under that define ot_s81_hc_ccr_align instantiates
# ot_s81_hc_ccr at its module defaults (HALF 0, RLY 1, RF 1) and the composition never completes (r5, 2026-10-13); the
# probe instead proves the soft instantiation elaborates each pad leaf at exactly its hardened default tuple.
#   hc_tile_bench.sh <out dir> exact [tiles]   probe run: bit-exact AND every probed tile (default all) is elaborated
#                                              only at its routed parameter tuples; prints "RUN <tag> pass"
#   hc_tile_bench.sh <out dir> <tile>          that tile's one-edit mutant; must print "RUN <tag> fail"
# One shared bench for both families (pad_*, ctnl_l*) and crooty_w: the tile is the argument.
set -euo pipefail
out=$1; what=$2; probes=${3:-all}
PKL_SHA=8c18c0655ccf6a14
for c in "${S81_SU_CASES:-}" /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl \
         /srv/opentallas-scratch2/claude/s81-suhc/su_cases_v2_ildr.pkl "$HOME/s81-suhc/su_cases_v2_ildr.pkl"; do
    [ -n "$c" ] && [ -s "$c" ] && { pkl=$c; break; }
done
[ -n "${pkl:-}" ] || { echo "hc_tile_bench: su_cases_v2_ildr.pkl fixture not found on $(hostname)"; exit 97; }
got=$(sha256sum "$pkl" | cut -c1-${#PKL_SHA})
[ "$got" = "$PKL_SHA" ] || { echo "hc_tile_bench: fixture $pkl sha256 $got != $PKL_SHA"; exit 97; }
[ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$out"
python3 tools/s81_suhc/hc_gate.py prep --cases "$pkl" --out "$out" --ng 256
shape="--ng 256 --hier 3 --cnl-pin 1 --chain-step 6 --lane-specialize 1"
if [ "$what" = exact ]; then
    python3 tools/s81_suhc/hc_gate.py run --out "$out" $shape --tile-probe "$probes"
else
    python3 tools/s81_suhc/hc_gate.py run --out "$out" $shape --tile-mut "$what" --tmax 40000
fi
