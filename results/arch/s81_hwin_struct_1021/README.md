# HWIN regional admission successor, 2026-10-21

**Default-off source candidate; no physical qualification or release adoption.** Source base aff1c1ca862cc0cda48be402cbd5d993171a0ea9 has exactly the same three HWIN capture source files as failed c21r e20095385d2024cabe267f4227e1fb17c24dac90. Existing source changes only when LOCAL_RECORD=1; its default is0. Original c21q/c21r failure records are preserved under failures/ and remain authoritative.

## Actual failure and structural change

Current daemon jobs c21q@3d41d2ba6 and c21r@e20095385 are NEEDS_RTL: TT setup-148.19/-141.73ps, FF hold-8.26/-11.76ps, DRC0. These are actual TT pathfinding results; SS sensitivity is separately negative. Stale review/waiting rows are not evidence of live jobs or closure.

The actual routed TT violated path in c21r_routed_tt.log runs from g_compare_copy[1].cmp_r[2] to g_event_mem[15].g_record_copy[1].rec_r. It combines identity equality, a47-entry duplicate reduction, record admission and distribution to all event memories and slot writes. Data arrival1222.75ps vs required1081.02ps gives-141.73ps. The first printed reset-recovery path is MET and is not this setup failure. FF's distinct failing path is payload.wdata[16] -> SRAM wd_in[0]; this candidate does not claim to fix it.

LOCAL_RECORD=1 replaces the shared duplicate flag on record consumers with independent kept regional cones: four groups of<=4 event memories and six groups of<=8 slot writes at47slots/16events. Every region has two reset-distinct10-bit user landing registers (each compares<=24 identities), an explicit eight-entry partial reduction, and a kept duplicate-region module. Each regional duplicate result drives<=32 record flops; global udup remains for original bookkeeping/diagnostics. No valid, transaction identity, reject rule or output edge changes. LOCAL_RECORD=0 aliases every regional duplicate to the original udup and adds no reset region.

## Model and cost

Sizing before build:10 duplicate regions, each47 comparisons, require200 extra user landing FFs,20 extra reset leaves and one additional reset group (221FFs total at the production parameters). There are470 regional10-bit equality comparisons in addition to the original47-entry checker. The expected trade is more logic/user copies for a shorter, local admission distribution. No area or timing gain is inferred from the model.

Added decode/config/start/output latency is **0 cycles**; the existing exact waveform miter checks this against both frozen HWIN21cb and early-capture references. Existing SRAM macro count, memory shape and ports remain unchanged. Technology-independent full-shape paired synthesis (ep7 unit35900, exit0) measured69,564 ->80,098 cells (+10,534/+15.14%),12,224 ->12,424 FFs (+200),84 ->84 SRAM macros. Plain synthesis can share relay state differently from the native kept-cell flow; the221 source-level FF addition is not a native census. Reports are cell-inventory sizing, not mapped area or timing.

## Bench reproduction

Run `bash tools/s81_dv/hwin_struct_1021/run_all.sh OUTDIR` on an admitted fleet host. This runs only the existing production47slot and2slot waveform/protocol benches and existing norelay/eastcopy/eastdue/mut2 negatives. The bench enables LOCAL_RECORD=1 in the DUT and retains both reference instances, configuration-edge shifts, pointer assertions, event/head/control comparisons and output comparisons. Expected negatives must match their causal assertion text, not merely exit nonzero.

The source-pinned historical package is tools/hwin_private_package_1019 from e20095385d2024cabe267f4227e1fb17c24dac90. If absent, run.sh materializes it into OUTDIR/deps with git archive. Its three frozen CBREF source hashes remain checked by the original script. The candidate branch does not import or alter that package or old kits. Paired synthesis uses synth.sh (which also materializes the pinned package when absent) and blackboxes the actual64x16 SRAM; its first top-chparam launcher hit a Yosys module-name assertion and is retained separately. The successful recipe uses an explicit wrapper.

## Physical qualification still required

The old kits' native fences, exact source-netlist hash and planning population receipt are tied to unchanged HWIN21j source. They cannot be reused for LOCAL_RECORD=1. No new kit/gate/route is launched here and no guard is removed. Required next work is mapped sizing/census, regenerated exact native cell/macro/fence manifests and a current source-bound planning/actual occupancy proof, followed by a new structurally reviewed kit. Preserve the original failures. The independent FF SRAM write hold path and TT output slack also remain obligations.

Safe-design disposition before a future gate:

| Check | Current evidence / remaining work |
|---|---|
| Pins | New user inputs land in reset-distinct FFs; physical locations not yet proved. |
| Reach | Local regions are the structural intent; native segment proof required. |
| Fanout | Source model bounds user comparisons24 and regional admission32; mapped census required. |
| Depth | Balanced eight-entry partial reductions and local cones implemented; mapped depth required. |
| Storage | No new table; existing SRAM macros retained. |
| Floorplan | Old exact manifests ineligible; new area/band/channel/40..60% proof required. |
| Clock/reset | Same streaming clock,221 additional FFs; physical tree/recovery/80ps spread proof required. |
| Schedule |0 added cycles, exact existing waveform miter; no calendar change. |

## Measured protocol result

Admitted bench unit ot-epyc5 oth-ubuntu-3505568-1792601223 completed exit0. Production47slot/16event case:188starts,2528fires,17545 CBREF and early-capture miter edges;2slot case:8starts/8fires,1705 miter edges. All hslot/hwin faults0. Existing causal negatives caught: norelay CONTROL c9, eastcopy EVENT_STATE c20/e8, eastdue boot-count event4, mut2 QUALIFIED_HEAD c1068/e0. Exact logs are under benches/. A post-bench comment clarified admission fanout8->32 without changing RTL tokens; record.json retains the tested SHA and final source SHA.
