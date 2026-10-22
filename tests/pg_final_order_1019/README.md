# Final PG preflight ordering repair

The strict final-report entry now calls the existing ot_pg_final_guard before returning to canonical final_connect global_connect. The final write guard remains. No native binder, domain rule, RC policy, strict schema, source-shipping policy, or opt-in default changes.

Callsite inventory in current source: tools/ref_tile/ref_route.sh:63 is the sole production source registration, --step-tcl PRE_FINAL_REPORT=physical/common_flow/native_pg_bootstrap.tcl. tools/ref_tile/ref_tile.py:2314 inventories the source; tools/closure_loop/helper_overlay.py PG_HELPERS inventories frozen strict payloads. There is no nonfinal production bootstrap callsite. Immutable ORFS final_connect (SHA cc85781e0387a787e2ac32a43db004390c5e62130f69a109b08cdaed836f4580) loads 6_1_fill, sources PRE FINAL_REPORT, propagates clocks, then global_connect. final_report (SHA 6635cf09989eeb9cb5d4e6f03081cfebf1dbe8d796828e6a0b34854956c93e9e) sources it before orfs_write_db 6_final.odb.

## Actual composed native proof

Unpinned ot-run 4GB/1CPU/2GB selected ot-epyc7, unit oth-ubuntu-221981-1792450598, exit0. Image openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29. Tool/library/LEF hashes are in evidence/output/tool_libs.sha256. Inputs/source checked before and after. Source strict CTS checkpoint SHA 09b8507cf2f62428641a60ccc59d83e0767dbdb939f7c45fe23c0cc29f7cdc83, 510 PG terms, 318 bound/192 unbound, remains immutable. This is a manually executed native composition test, not an accepted closure-loop job.

The canonical final_connect and final_report files are byte-identical retained scripts. Only load/clock/SDC-output adapters replace unavailable stage orchestration: actual read_db, global_connect, helper and write_db execute natively. No timing libraries/RC/SPEF analysis is run. This is PG entry ordering evidence, never timing, conductor, export or full-PNR qualification.

- Preserved original bootstrap composition: rc0, global_connect2, write1, binding state changed. It hides the 192 late-unbound terms before its write guard.
- Fixed strict original checkpoint: OT_PG_FINAL_LATE_BINDING_REFUSED count192, global_connect0, write0, binding state unchanged.
- Protected-unbound fixture: same refusal/count0 GC/count0 writes/unchanged bindings; no protection clearing.
- Default-off original checkpoint: rc0, canonical global_connect1/write1, exactly original default behavior.
- Distinct all-bound TEST fixture: explicit global_connect immediately after load, before analysis, then serialize to output/allbound_fixture.odb. Fresh-process fixed composition rc0, GC3/write1, unchanged binding state, 510/510 correct. This fixture is not our repaired real checkpoint or an adoption claim.
- Dirty all-bound control: OT_PG_FINAL_RC_DIRTY_REFUSED, GC0/write0.
- Wrong native rail role and overlapping native voltage-domain fixtures: OT_PG_RULE_ROLE / OT_PG_AMBIGUOUS_DOMAIN, both GC0/write0.

All eight cases PASS. First native attempt output_api_failure_01 is retained: seven controls passed, domain control failed because the test omitted native dbBlock_addGlobalConnect do_connect argument. A nonexistent guessed LEF hash path also printed an error. Corrected test uses actual native NULL region/do_connect0, and hashes all actual platform LEFs. No production change followed the first attempt.

## Shipping and remaining scope

helper_implications.json: default49 is byte-identical; strict53 changes bootstrap only; no path-count/schema/default changes. New strict plans freeze the new bytes; existing immutable old strict jobs must retain old payloads and ordinarily refuse drift. Bootstrap belongs to the 78-path runtime closure, so ROOT/sole merger must drain before publication and review coherent source + all78 runtime bytes/modes before restart. No source published and no runtime/service mutation by this lane. Parent owns combined full cohort with the separate frozen SDC fix.

Gate-Rule classification: tightening requires=pg_strict. Previously repaired-late strict final bindings now refuse before canonical global_connect. General PG-birth coverage gaps, routed-model refusals and absence of full strict PNR remain HOLD; this repair does not broaden those claims.
