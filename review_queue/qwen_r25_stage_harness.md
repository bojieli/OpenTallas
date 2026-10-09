# Qwen R25 dispatcher, mask and quarter service review

Prepared 2026-10-09. Owner: Codex qwen_hbm_unify/stage_harness. Branch: codex/qwen-r25-stage. Claude is the main coordinator and reviewer; no main merge is performed by this owner.

The production transport preserves owner74 fields job[31:0], generation[35:32], token[53:36], position[73:54]. The four-quarter structural top uses OWNER_W74 and QUERY_RELEASE1. Each query waits for a checked owner/slot acknowledgement before fetching another program or reusing scratch. Control gates use mock arithmetic completions and are explicitly scoped. Actual TU publication capture, visibility and lease drain must drive that acknowledgement; arithmetic done does not qualify release.

Completed immutable evidence:

- 23a8fb0d5: checked query-release positive and wrong-owner negative gates pass; actual mask full-p4 capacity8224, lengths8192..8195, 32896 comparisons, 23552 exhaustive SECDED8 cases and transient/output data-bit CE/UE pass. Legacy73 protected pipeline route fails TT setup -0.211558ns, hold +0.0123366ns, clean DRC/antenna.
- c201f0957: actual owner74 protected pipeline route fails TT setup -0.213830ns, hold +0.0166126ns, area3287um2, clean DRC/antenna. Constraints preserved.
- 178b541e3: copy-only protected context successor passes full-p4 and actual owner context data-bit CE transfer/destination double-error rejection. RTL0f11ee283 copies unchanged codewords only; original checked occupancy update retained. Parameter CONTEXT_CODE_COPY defaults off, model adds no cycles or bits. The first occupancy-XOR variant failed and remains preserved at92af07add; its invalid indefinite-wait simulation was validity-canceled with receipt06e18c667.

Already progressing routes are preserved: legacy dispatcher PID2756283 on ot-agidock128; protected context-copy pathfinding route launcher4147007/driver4147190 on that host. The latter was launched before the new review-before-route directive. It uses 200x200um, .833333ns, TC/BC, 60/25ps, registered harness with two added cycles and external IO false paths. These are standalone pathfinding measurements with no context closure or headline credit. No further structural route will launch before Claude approval.

The actual N256/M64 full-FP quarter service bench remains queued on ot-epyc4 under guard128GiB, launcher2360296/observer2360298. Source composite: quarter5449dfcc4, compilerd5225192c, actual dispatcher/query-release and service bencha2b3b4f53. It models persistent262144-word VM, CONST0word262143, actual337/273 service replies and write-visibility reads, full RMS4096 and p4 softmax lengths8192..8195, and reads expected output before checked scratch release. No numerical RTL pass or cycle credit exists yet. Fleet confirms genuine future-growth claims prevent admission; no guard bypass or duplicate build.

Source inventory and analytical sizing are in tools/qwen_r25_su_dispatch_model.py and tools/run_qwen_r25_quarter_service.py. The unified uarch hook must remain integrated. Additive LIVE records are under results/fleet_viz/element_registry/qwen_r25_context*.json; dependencies are string arrays. Production timing boundaries and real TU release endpoint remain pending parent ownership.
