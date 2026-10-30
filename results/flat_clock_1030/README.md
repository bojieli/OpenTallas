Both T7 endpoint-corrected native cohorts have passing joint TT/FF clock models
and exact empty-row driver sites. `summary.json` records actual model values,
immutable source/checkpoint identities, packet paths and the remaining gates.
The compact input files retain every proposed driver and real sink by name;
large native ODBs, waveform outputs and Liberty files remain in scratch.

Rendered and LOOKed: both `t7{a,b}_flat_clock_sites_v4.png` paths in the summary.
The trees retain16 primary input locations and each declared forwarded root,
place local drivers near actual sinks, and use real empty sites while all
existing FFs, TAPs, logic and DATA/reset connections remain unchanged. The
landing bands are crowded; initial2/5/10um site searches failed. Revised planned
sites moved at most11.023/10.145um before full TT/FF re-modeling. No occupied
site was accepted and no existing cell moved. Actual final leaf reach is
23.112/37.800um. The images show analytical topology, not routed wires.

The20ps window uses consistent late/early calibration states and each native
FF's actual active edge. Rise/fall common-path duty distortion is retained;
ideal half-cycle phase remains in the unchanged native library/SDC. Ordinary
pair bounds include per-master SPICE and g021 AOCV with actual tree CPPR.
Forwarded/primary pairs use the existing416.5ps clock-damage window; the356.5ps
SDC limit is DATA-only. Native tap_window180 is an available kit hold budget
(`die_sta_related.kit_windows`), not extra180ps clock damage added a second time.
Full native STA, landing/frame checks and signoff remain required.

All packets have `physical_authority=false`. Source/model preparation is ready
for root review; no P&R was started. Use only the exact complete corrected
checkpoint, including the endpoint owner's RRL moves and post-place mixed
masters. A fresh SYNTH or changed cohort needs new inventory and targets.
T6's same-k horizontal endpoints remain OWNER-held; this result does not
qualify T6 or authorize a recovery run.
