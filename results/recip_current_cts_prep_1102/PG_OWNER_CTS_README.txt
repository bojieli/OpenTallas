SOURCE-ONLY private RECIP CTS lifecycle proposal; no native CTS qualification.
Keep original manual OT_PG_STRICT UNSET. Use exact e19 helper and module8c9
under NEW dependency names /work/pg_native_qualified_562.tcl and
/work/pg_native_8c9.so, preserving every original94 input. Source this helper
as /work/pg_cts_canary.tcl; it does nothing native until begin after actual
3_place/libs/rules load. No old tree or library clock model is transferred.

API, lowercase tag cts:
1. ot_pg_cts_canary_begin cts after load and before ENTIRE original PRE.
2. ot_pg_cts_canary_after_pre cts immediately after original PRE, before
   repair_clock_inverters. Requires the actual MM ot_mcc_cts_orig wrapper.
3. ot_pg_cts_canary_before_post cts before ENTIRE original POST.
4. ot_pg_cts_canary_finish cts after POST/before primary save; idempotent.
Outer driver must also always attempt finish on every error/completion,
preserve primary errors and refuse nonlocal returns/full POST not reached.
No exit may bypass cleanup; no source flag, algorithm or hook may be dropped.

Logs PG_CTS_CANARY_cts.jsonl (exclusive new file). Requested CTS and final
original ot_mcc_cts_orig calls are distinct, with exact arguments and native
counter deltas. repair_clock_inverters and repair_design/timing are separate;
BEFORE_POST and POST phase distinguish later setup repair. Native errors are
preserved if PG remains valid; a failed PG audit is fatal. END requires real
native audit/end and explicit inactive status. Values are JSON strings;
argv is an exact Tcl list and native fields are Tcl dictionaries.

Current retained input is8994 direct CLK pins on netclk. Of12915 native inverter
instances, none touches clk. A zero-birth repair_clock_inverters result here
cannot qualify its general inserting path. Ordinary CTS arguments remain
-sink_clustering_enable -repair_clock_nets; macro wrapper adds nothing for0
macros. SKIP_CTS_REPAIR_TIMING=1 retains the full post_cts_setup hook, including
its original setup-only repair if needed. No CTS/STA/solver release follows.
Six source-only mocked instrumentation controls pass, not native proof.
