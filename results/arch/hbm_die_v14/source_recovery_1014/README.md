# HBM v14 source recovery

This publishes the cumulative v13/v14 die implementation missing from main, together with its real clock-root/COLL RTL wrappers, station/glue/view tools, explicit relay placement, and source-pinned congestion histories. It recovers a diagnostic candidate; it does not establish native binding or die closure.

The live run23 case on EPYC1 remains preserved under `hbmdie-v14/run23/sta`. Its own trunk CTS completed in310.54s; extraction collided with a superseded case container name and is now being recovered from its own database. `publication.json` records hashes, live-source identity, and observed limits. Replaying the live geometry requires `OT_HBMDIE_CONG=results/arch/hbm_die_v14/source_recovery_1014/cong_p2.npy`. The older v13 default history is retained because `r25gqn_v13` loads it during preset construction.

Main's S81 full-RTL die lint, current clock-case naming, and native component floating-point congestion parser are preserved. The HBM `ctl_top` direction is added to main's current lint. The generalized `tools/die_port_bind.py` remains the authoritative binding gate; the older HBM-specific binder is published only for historical diagnostic reproduction.

Next revision must embed the H-COLL registered credit-flow VM port as real per-child RTL, preserve compact SM transport state, and bind every master/reset/scalar clock to real RTL. Require actual binding PASS before a new die chain; require GRT overflow0, TT setup and FF hold closure before release. SS is sensitivity only.
