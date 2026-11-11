#!/bin/bash
# CPL-S81-SLICE explorer renders for the gated SLICE-C delta: before/after overlay (--delta on 99f) and the re-sited after plan
M=/srv/opentallas-scratch3/claude/cpl-s81-slice
X=/srv/opentallas-scratch3/claude/explorer-script/tools/fleet_viz/explorer_render.py
RC=/srv/opentallas-scratch2/claude/plan-route-1/release_cache.json
cd /srv/opentallas-scratch2/claude/plan-route-1/repo
mkdir -p $M/explorer_g
for T in c1x_C__t4 c1x_C__t8 c1x_C__t9 c3x_C__t1 iq_C__t1 lepe_mu_C__t1; do
  nice -n 19 python3 -I $X type --plan $M/plan_99f.json --type dsdv_slice_$T --repo . --delta $M/deltas_g/delta_SLICE-C_99f40d35.json --supply --release-cache $RC --out $M/explorer_g/$T > $M/explorer_g/$T.log 2>&1
  nice -n 19 python3 -I $X type --plan $M/plan_g.json --type dsdv_slice_$T --repo . --supply --release-cache $RC --out $M/explorer_g/${T}_resited > $M/explorer_g/${T}_resited.log 2>&1
done
echo EXPL_DONE
