# PG birth checkpoint — work continues, not a reset/handback

## Source and concrete capability

READY/pushed **8322bb073**, branch `codex/pg-birth-1102`, own WT
`/srv/opentallas-scratch/claude/wt/codex-pg-birth-0018` (based on ad4a556).
Root shared-code review/merge is pending. No global deployment or full ordinary-flow
canary is claimed.

`tools/openroad_pg_birth/native_pg_birth.cpp` is a small native loadable OpenDB
callback. It connects PG inside `dbInst::create`, after all ITerms/region exist
and before the constructor returns; validates master changes in native Before/
After callbacks. It is not a Tcl-return binding shim. Native module admission
pins executable SHA256
`21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846`,
ORFS image SHA256
`16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
OpenROAD source `6cb3f2b704604a8961573218e1c8adaae9fe9937` / 26Q3-1510.
83 official public headers are hash-pinned; `fetch_headers.py` + `build.sh`
compile this extension in the pinned image without rebuilding OpenROAD.

Updated canonical `physical/common_flow/native_pg_binding.tcl` supplies:

```
ot_pg_native_birth_begin /work/nativepgbirth.so
# actual source-owned native operations
ot_pg_native_birth_end
# or: ot_pg_native_birth_eval /work/nativepgbirth.so { ... }
```

Load libraries, ODB and rules first; initial native PG audit MUST PASS. Native
C++ callback status/current DB identity/audit admit **only repair_design and
repair_timing** through strict unsupported-birth guards. No module/default
behavior is unchanged. Fake Tcl capabilities, inactive callbacks, CTS and GPL
remain refused. Context reloads inside the transaction refuse. Flat all-instance
`.*`, literal-PG rules only; regions/ambiguity/unknown pins/wrong existing PG
refuse. No protection clearing or late existing-PG repair.

## Actual native evidence

All owned jobs terminal; **no live own jobs**.
Epyc2 root: `/srv/opentallas-scratch2/claude/codex-pg-birth-0045`.

* TT repair_design mechanism stimulus: **5786 births +19 swaps**, control11572
  PG opens versus callback0 /39054 native terms. Existing source/frequency was
  unchanged; fanout8/max-wire20 are explicit mechanism-test stimuli.
* FF routed-RC repair_timing -hold: **1719 births**, control3438 opens versus
  callback0 /30920 terms. No clocks/margins relaxed.
* Strict-v1 repeats first case with5786/19 and PG0. Fake Tcl capability/inactive
  callback/unvalidated CTS/reload controls reject, callback cleanup verified.
* Seven native negatives reject ambiguity, regional rules, signal-pin supply
  rule, existing wrong domain, protected unbound, unknown newborn PG pin and
  wrong-role master swap. Existing state unchanged; rejected-new-cell cleanup
  occurs only after uninstall, never analyzed.
* Independent fresh saved-DB native audits PASS39054/30920/39054,0 failures.
* Control/callback instance master/pose/orientation/status/DNT/source flags,
  functional connectivity/netflags, DATA/CLOCK wire opcodes/guides and BTerm
  geometry are byte-identical in all3 paired comparisons.
* 15 targeted existing/helper dependency/ECO hook/staging tests pass.
* Observed runtimes: design14.74→15.64s; FFhold18.06→44.57s. Peak<556MB.
  No zero-overhead/general benchmark claim.

Compact logs/receipts/repro are committed in
`results/flow/native_pg_birth_1102/`. Failed preparation/header/initial deletion
hook/dynamic invalid-master STA SIG11/multi-read ORD-0047 harness attempts remain
preserved; corrected native controls use a real loaded master. No target timing
or SIGNED credit inferred.

## Exact artifacts / staging

Immutable v1 module:
`epyc2:/srv/opentallas-scratch2/claude/codex-pg-birth-0045/v1/build/nativepgbirth.so`
SHA256 `8c9e1eef9ec6451a5bc1710da15fe683785aa8791d21099e4ee9ec30fee0a93b`.
Updated helper in `.../v1/native_pg_binding.tcl`. v0 module/source remain under
`.../validated_v0` (reference only), never overwritten.

`tools/openroad_pg_birth/stage_grt.py --kit OWN_FRESH_COPY --module MODULE`
places native begin at the VERY FIRST PRE_GLOBAL_ROUTE action (before original
PRE holdpad/AP/ECO), original POST then native end last. It preserves existing
chains/old helper/config prefix/provenance, records a tool/config delta, and
claims STAGED_NOT_RUN. MM scenes are loaded before PRE in the actual normal
session; any separate OpenROAD process requires its own installation.
FLOW has copied v1 into its owned L4 true-DRV-checkpoint PREP, no setup/DRT,
root review/dispatch pending. No AP file edits by this lane.

## Sole upcoming LLfd CTS canary (not dispatched)

S81 parent/core owner holds the one already-reviewed CTS from actual rebound
3_place SHA
`6962c6d7c2229b68c3ba0961303f8b2cb14f718b3486804d78c2b06d59a4b266`.
13 fixed clock cells, membership-only441 rebind, source/PG/model previously
reviewed. No GEN/PLACE repeat or duplicate CTS.

Owned instrumented fresh copy PREP:
`epyc2:/srv/opentallas-scratch2/claude/codex-pg-birth-0045/cts_llfd/{kit,run_cts.sh}`.
Only PG helper/module + outer PRE_CTS / last POST_CTS wrappers/config delta;
3_place hash unchanged. Root needs to review/authorize exact hook scope before
normal8GB2T ot-run dispatch. Wrapper refuses OT_PG_STRICT=1 because CTS strict
admission is NOT yet granted; no strict bypass. Normal-mode canary would add the
real native callback to the already-authorized normal CTS and require actual
pre/post/fresh-saved PG0 and ordinary source/clock/geometry gates.

Pinned ORFS `cts.tcl` invokes PRE_CTS immediately after load_design and before
repair_clock_inverters/clock_tree_synthesis. Existing PRE hold_budget/core CTS
open-net logic retained; original POST includes normal setup/DPL/measurements.
Pinned CtsOptions create callback only records buffer counts; EST callbacks
invalidate only. TritonCTS creates top buffers/dummies via native dbInst::create,
and its placement estimate occurs after construction. Actual CTS capability
remains unqualified until the canary; GPL/Hroot also remains HOLD pending its
callback ordering and actual scoped vehicle. No new owner question.

## Continuation after checkpoint (02:19 local)

Epyc2 scratch fell below the shared50GB floor; no override or job launch.
The same owned LLfd PREP was copied directly to
`intel2:/srv/opentallas-scratch/claude/codex-pg-birth-cts-0219` (344GB free).
Only own `run_cts.sh`/`run_saved_census.sh` root paths changed; kit/input/module
unchanged. Existing S81 read-only savedCTS census and independent savedPG audit
are staged in `audit/`; no added estimated STA. Review remains pending and
there are still no own live jobs.

Exact-source continuation: OpenSTA submodule
`509913b1398b36eda23caa1f1f380167465dceee` makeInstanceAfter/replace* callbacks
perform graph/cache invalidation, not RC estimation. GPL nesterov callback
creates/resizes geometry bookkeeping and filters PG ITerms. Future Hroot
candidate uses timingDriven0/routabilityDriven0, so a scoped placement would
qualify that no-birth continuation only. Geometry owner is independently
closing its completed2338 inputPG on an admissible host. GPL/CTS strict
admission remains unchanged.
