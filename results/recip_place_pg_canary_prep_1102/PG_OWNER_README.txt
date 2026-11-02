PRIVATE121 instrumented ordinary PLACE canary SOURCE PACKET; no CAD from this packet.

Stable helper SHA8501261ee6807f47a9ec5178951b18eb270b7fdf6aea3c690ab1513bd4bae914.
Dependencies are NEW filenames so all94 original inputs remain unchanged:
/work/pg_native_qualified_562.tcl SHAe19c5fd9872e37f68d610e2dc46608359c9970b7c9e6de84f546f3b3c3ea3a2d
/work/pg_native_8c9.so SHA8c9e1eef9ec6451a5bc1710da15fe683785aa8791d21099e4ee9ec30fee0a93b.

Exact APIs: ot_pg_place_canary_begin(STAGE), after_pre(STAGE), finish(STAGE),
where STAGE is the lowercase source script basename. Source helper definitions
before entire preserved stage. Begin AFTER actual load, BEFORE entire original
PRE; after_pre AFTER all original PRE (including face alias setup). It records
PRE changes, requested global_placement separately from FINAL ot_gpl_native
attempts, plus port/resizer/etc calls separately. Native counters before/after
are cumulative create/swap/bind EVENTS, not retained instance-count deltas.
GPL virtual resizing/rollback or failed attempts must not be silently relabeled.
Argument-presence fields are recorded; never infer actual GPL modes from make
flags alone. Native plain/skip/fallback/no-birth is not timing-driven birth proof.

Finish is idempotent; prior failure stays failed. It attempts all observation
trace removals and canonical native end, explicitly checks inactive status,
records and closes log. Caller catches ENTIRE original stage and always calls
finish preserving original errors. An uninitialized finish is accepted only for
stock IOcopy/no-load branch; this is SKIPPED_NATIVE_BODY, not qualification.
Keep stock IOsave-before-POST order; other stages finish after POST before save.

The actual reviewed manual121 environment has OT_PG_STRICT UNSET. This helper
requires it remain unset, does not change1 to0, and asserts the qualified helper
still reports global strict GPL support0. The real compiled callback protects
constructor PG in the experimental process; no environment-only capability,
renamed unsupported-guard bypass, main admission or production claim is added.
Input PG0/native persisted rules are mandatory at EVERY stage. No late bind can
provide earlier birth credit. If FP/source inputs fail, preserve them and use a
separately guarded saved-copy repair; do not weaken this precondition.

Source-only seven controls PASS (also independently rerun by nf2 child):
requested/plain/port separation; real-error fallback; ordinary native error;
PGerror overrides retryable fallback; sticky end failure; inactive status check;
IO-only no-begin skip. test_helper.py uses explicit Tcl mocks and is NOT native
PG/GPL qualification. Child owns exact-entry patch/frozen-script reversibility,
normal MM/dry integration; parent reviews the complete packet before ONEcase.
