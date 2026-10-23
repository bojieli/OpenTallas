Safe-design review before synthesis/native admission

1 Pins: new command and all output ports register at face; raw original pin stage preserved.
2 Reach: outline302x151 or345x173, all local reach within405um; routecrossings handled in separately landed die route.
3 Fanout: mapped native32 census PENDING. Gate must stop before layout on violation.
4 Depth: SRAMread -> normalized byte/format selectioncapture -> conversion/output. Real5edge latency measured. Native depth PENDING.
5 Storage:2 actual128x256 SRAMmacros, 8192bytes/lane, payloadpipeline below2kbit.
6 Floorplan:2macro regularrow >=20um channel, fullwidth cellband, enlargedoutline, synthesis fill PENDING; no shrink.
7 Clock:singlelocalroot, TT/FF spread PENDING, 30ps boundaryholdmargin.
8 Schedule:fixed W62 commands, no ready/credits, exactepoch/full ownership, lastread or release-only frees bank. 5edge localconversion +5route measuredseparately.

Structural native repair: kept16bit rawselectors; per8slot landingseen and controlcopies; kept2bit normalizedcaptures and scatter; per16bit converters; no sharedbyte/destinationbarrel. Epochbank/reset copies preserve original pin and raw edges; conversion adds1edge. Actual source census pending; old49violations retained in results/rtl/hbm_dma_load_static_1021/native_v1_fail.

Native2 max76/350 violations archived; native3 structural source0a9f055cf uses8x4 registered local byte decodes,8 kept source-payload copies,quarter conversion outputs,local countersclear and separated resetcontrols. Localconversion expected5edges; 1480positive/mut causal already checked, fullraw/actual384/bank1 tests running. Census remains PENDING, never aphysicalPASS.
