#!/bin/bash
# Per-tile qualification of the hard S81 HC leaves by the production-shape composition gate (s81hc-1013 r5; see TILES
# in tools/s81_suhc/hc_gate.py).  NG 256, HIER 3 (half-octet tiles + split column roots + chain-tail split), CNL_PIN 1,
# CHAIN_STEP 6, LANE_SPECIALIZE 1.  The per-tile runs are the SOFT composition (every parent passes its parameters); the
# probe proves each leaf is elaborated at exactly its routed tuple.  `exacthard` is the same gate with
# OT_S81_HC_PAD_HARD (pad leaves and the ccr core instantiated with NO parameters = their hard views): it runs at the
# production configuration since ot_s81_hc_ccr's defaults are the production core tuple (r6; before, HALF 0 / RLY 1 /
# RF 1 and the hard-pad composition ran to TMAX).
#   hc_tile_bench.sh <out dir> exacthard [tiles]  as exact, with OT_S81_HC_PAD_HARD; prints "RUN <tag>_ph_probe pass"
#   hc_tile_bench.sh <out dir> exact [tiles]   probe run: bit-exact AND every probed tile (default all) is elaborated
#                                              only at its routed parameter tuples; prints "RUN <tag> pass"
#   hc_tile_bench.sh <out dir> <tile> [hard]   that tile's one-edit mutant (hard: under OT_S81_HC_PAD_HARD); must print
#                                              "RUN <tag> fail"
# One shared bench for both families (pad_*, ctnl_l*) and crooty_w: the tile is the argument.
set -euo pipefail
out=$1; what=$2; probes=${3:-all}
PKL_SHA=8c18c0655ccf6a14
for c in "${S81_SU_CASES:-}" tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl \
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
elif [ "$what" = exacthard ]; then
    python3 tools/s81_suhc/hc_gate.py run --out "$out" $shape --pad-hard 1 --tile-probe "$probes" --tmax 40000
else
    hard=0; [ "${3:-}" = hard ] && hard=1          # <tile> hard: the mutant under OT_S81_HC_PAD_HARD
    python3 tools/s81_suhc/hc_gate.py run --out "$out" $shape --tile-mut "$what" --pad-hard $hard --tmax 40000
fi
