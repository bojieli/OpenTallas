# Forwarded clock continuity guard and protection proposal

The actual HEAD HOST first saved4_1_cts loses A on two declared BUFx24 forward drivers. Three others remain correctly connected through the CTS buffer tree. Both bad inputs stay NULL through route/final, and post-route LEC correctly reports two gate-X clock outputs. Original source exports connect all five before CTS; missing-path warnings appear before cts_post. The exact operation inside CTS still requires an instrumented bounded test. The preserved negative fixture is the original host_b2t4_1_cts, not a fabricated disconnected model.

This source-only patch makes future generated fwd_buffer kits carry a read-only declared-export checker. It checks the declared endpoints/driver/master, non-null A/Y, Y-to-output connection, and actual timing-graph fanin root of A. It accepts a real CTS buffer tree between A and the declared source port; a direct-net equality would incorrectly reject the three good native paths. PRE_CTS checks the newly generated connections. The shared POST_CTS hook checks entry before balance/repair, then checks exit after PG. A failure stops the future flow without reconnecting nets, resizing, moving cells or changing the source/clock/output comparison contract. Legacy tie-form kits do not gain a new checker.

Meaningful read-only native test: normal4GB2T EPYC2 unit1797808-1793619084 exit0. On the retained actual negative fixture, the checker passed ad_o/au_o/bd_o with their real buffered roots, rejected bu_o/h_rx_ft_o with NULL A, and rejected a deliberately wrong declared source for the connected ad_o path. The test catches the two known errors only to verify classification; the generated production hooks do not catch or waive a failure. Input ODB mounted read-only; no DB write, CTS, route, reconnect or timing readout was executed. Existing export/bit0 targeted tests passed12/12.

Initial audit dispatch was NOTRUN on EPYC2 scratch-floor48GB, then an Intel1 waiter had no native outputs and was officially canceled NOTRUN. Reclaiming only owned disposable copied inputs (originals remain on Intel2; unique moved SPN input/output and native negative fixture retained) restored EPYC2 above50GB floor. No floor override, foreign cancellation or admitted restart occurred. Full current test artifacts remain EPYC2 `/srv/opentallas-scratch2/claude/codex-head-export-guard-1102`; native negative input is its hardlinked readonly input/base_4_1_cts.odb.

This patch is for a future source event. Frozen703 kits, their source snapshots and active jobs were not edited. It does not fix or qualify the existing broken HOST outputs and grants no source equivalence, clock phase/insertion, parent IO or SIGNED credit. The exact generated forward master is checked; a planned driver-class change needs corresponding source review. Native vector-bit0 runtime coverage is not claimed; existing bit0 generation tests pass.

The separate protection experiment below is a proposal, not active source behavior. The continuity guard is useful independently: it exposes this failure before long post-route work.

## Bounded protection experiment for ROOT scope

Use a private copy of the exact retained HOST3_place and normal PRE_CTS source/hook. Save the post-PRE_CTS connections, then consider protecting only the newly created declared forward-driver instances:

```tcl
foreach row $::ot_cland_export_links {
  set inst [[ord::get_db_block] findInst [lindex $row 2]]
  $inst setDoNotTouch 1
}
```

Keep source tap nets available to CTS: clk_t8 also feeds728 real register sinks, so a source-net don't-touch would interfere with the real tree. Preserve graph, cycles, public pins and all existing FF sites. Run the single normal CTS stage with the checker before and after, inspect actual driver placement/overlap/PG and source-root continuity, and retain any failure. Existing PG helper handles protected unbound supplies, but PG0 must still be measured.

The effect of instance protection on CTS input rewiring and DPL legality is unmeasured. Multiple forward drivers initially share a source location; protection may require a separately reviewed legal-site treatment. It may also cause CTS to refuse rather than repair this topology. Do not interpret either outcome as clock qualification. Only a successful bounded native result followed by actual LOOK and normal clock/timing/source gates can support a future repair. A post-CTS reconnect of an unrouted input is not established by this proposal.
