Safe-design review before synthesis/native admission

1 Pins: new command and all output ports register at face; raw original pin stage preserved.
2 Reach: outline302x151 or345x173, all local reach within405um; routecrossings handled in separately landed die route.
3 Fanout: mapped native32 census PENDING. Gate must stop before layout on violation.
4 Depth: SRAMread -> normalized byte/format selectioncapture -> conversion/output. Real3edge latency measured. Native depth PENDING.
5 Storage:2 actual128x256 SRAMmacros, 8192bytes/lane, payloadpipeline below2kbit.
6 Floorplan:2macro regularrow >=20um channel, fullwidth cellband, enlargedoutline, synthesis fill PENDING; no shrink.
7 Clock:singlelocalroot, TT/FF spread PENDING, 30ps boundaryholdmargin.
8 Schedule:fixed W62 commands, no ready/credits, exactepoch/full ownership, lastread or release-only frees bank. 3edge localconversion +5route measuredseparately.
