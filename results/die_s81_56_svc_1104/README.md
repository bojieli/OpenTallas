# S81 svc band plan event (DIE-S81-56/PLAN 11-04)

Replay: `physical/die_plan/s81/delta_svc_band_1104.py SRC_PLAN OUT_PLAN physical/die_plan/s81/delta_svc_band_1104.json SRC_SIDECAR OUT_SIDECAR`
on the merged RF-EG plan; then `delta_xrt_rfj_1104.py` (xrt step).

Estimate and form:
- Needed: every svc type a legal site for its macros. svc_hi rs 45, svc_hi pvso_entry 181, svc_lo 66 (pilot elaboration).
- pvso's 136 extra 32x64 ingress macros set G_HI. Result: svc_lo +319.68 um Y, svc_hi +293.76 um Y.
- Die 31950.72 x 25358.4 um (<= 26 mm reticle).
- 28 planned die.channels `svcband_<lo>__<hi>` (76 ports, M7/M5/M3) instead of spacer partitions.
- Macro sites are `contents[]` rows in the band.

Reset wave: the band lengthens svc trees and shifts rows. Unpinned, that flips release races and rewrites 22 non-svc trees.
`reset.in_sites`, `reset.parent_pins` and `reset.keep_outs` (opt-in, default off) hold them; 5 non-svc types still take one new out.

Not shown here: kit gen on the event, builds, die STA, LEC. GEOM is advisory (owner rule).
