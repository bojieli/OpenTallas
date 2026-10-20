# Existing STREAM c3r: finite read-only reconciliation

Pinned source c9be6ed8a5072fb754ecad0914b450c9f80be2d7, original ep7 job qfd_dv_stream_t3c_1020-c3r-c9be6ed8a. Snapshot shows ECO/hold_eco.a1, not CLOSED. Helpers remain the original verified c076 50-file overlay, contentSHA5b87a481c37d660435677effcce7c4a83aaf80103e1d3c98d009a50d92cc3a2a. No reroute/duplicate/source/helper change was made.

Actual cached RTL hashes match the successful10000edge/946emit/tworeset bench and all ten causal mutant records. Relative to old49ac29c7e, qfd_dv_stream_tile.sv changed; base qfd_dv_stream.sv did not. Current bench/source contract isDP2/DX2; pass/taps add1edge perhop versus t2, ownwrite removes1edge. Parent staticcalendar and compensation remain unbound.

Actual pre-ECO routed result TT+89.18/FF-0.66ps;16610/16610registers clocked,7174boundary. Actual routed boundaryspread94.0TT/87.4FF exceeds80ps; pre-gate68.8/65.3 cannot qualify finalroute. Intermediate existing ECOpass1 isTT+89.59/FF+13.84/DRC0 with1456addedcells; pass2 continues. These are pending snapshots, not final receipts or selected final metrics. On actualCLOSED, re-audit exact finalmapped native32(allfunctional/constant roles), PG, fullstage405, completeactualLibclockcoverage/spread, pins and parentcompensation before qualification.

Oldt2/t2c numericalCLOSED updates are recorded only as verdict diffs. They retain the earlier actualnative failure211>32/max69 and all parent/schedule holds; no adoption is inferred. Original c3 refusalCLOSED_STANDS is preserved. This packet imports no physicalview or helper.
