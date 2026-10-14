# Native fused TP8 attention service candidate

`ot_qwen_tp8_attention_service` connects lossless FP32 Q transport to the actual native H score/exp/Z body, its actual synchronous BF16 exponent memories, physical-stack V row response transport, the two canonical PV256 residue-pair trees, and the 32 independent final joins with the actual reciprocal. The harness never supplies an exponent or a reciprocal.

This is an explicit candidate source profile: compile with `KVD_HEADS=1`, `KVD_Q_FP32=1`, `KVD_QK_ONLY=1`, and `KVD_ECTL3`. Those macros default to the legacy profile when absent. New profile sources and common-clock functional adaptation have no inherited CLOSED physical qualification. The ordinary H body retains its complete K/V behavior with `KVD_QK_ONLY=0`; only the native profile ends its request generator and row consumer after K group0.

The descriptor is `{epoch[15:0], layer[5:0], position[17:0]}` with position <=8191 and context = position+1. `fused_program_capability` must come from a source-bound semantic-lowering validator; the original unfused image cannot assert it. The actual weight emitter can add required BF16 post-collective scales, so capability is independent of literal program word count. Q arrives as 32 ascending 512-bit FP32 beats; BF16 RNE conversion occurs in H at actual consumption.

K requests have 32 ordered engine queues (four stacks, eight engines). Each finite request adapter retains 128 entries, equal to H's DQ credit limit, through response retirement. External request stalls never pretend H has request-ready. K responses carry t, epoch, and layer; invalid tags, reordering, unsolicited responses, wrong type, or overruns cause a fault. V uses eight owned slots per canonical pair, with request stack selection derived from t[8:7]. Actual V data and tags are registered together with an actual exponent SRAM read for k=t[12:9], residue=t[6:0].

Results are 32 ascending registered 512-bit FP32 beats. A producer holds each beat under backpressure. `result_done` records only acceptance of beat31. It does not mean that vector memory committed any result. Native dispatch must wait for the separately observed 32 VM commit acknowledgements before dependent O projection or token completion. The service waits for finalizer release before accepting the next descriptor, and requires fresh score-phase clearing before admitting its V phase.

The functional harness uses actual Q/K/V input rows and canonical golden outputs. The full-width build uses the existing simulation-only FP32 add/multiply and fast-FP DPI stand-ins with their RTL latency/valid pipelines; it exercises the actual H/SFU/control/transport/SRAM/tree ordering rather than compiling every bit-level FPU instance. This is functional arithmetic evidence with that explicit substitution, and does not prove every full-width bit-level FPU instance or any physical timing. Its response model has a synthetic latency and intentionally does not qualify HBM bandwidth, physical routing, clock trees, workload rates, or a full token. The common-clock adapter also does not qualify the independent clock entries' delivery.

Build/run only under measured `ot-run` admission (initial requested class 32 GB, eight build threads):

```
bash tools/qwen_tp8_attention_service_build.sh obj
python3 tools/qwen_tp8_attention_native.py vectors --ctx 8192 --seed 1 --kind normal --groups 3072 --out vectors/full
obj/Vtb vectors/full steady
obj/Vtb vectors/full stalls
obj/Vtb vectors/full restart vectors/different_frame
```

The optional second directory in restart mode must contain an independently generated frame to test actual stale-state protection. The small-context PV implementation explicitly clears all 128 retained residues before each frame, adding 128 initialization edges; its operator proof alone does not qualify the composed small-context service. Live source archives are immutable, and the initial full8192 build used the pre-small-context version; subsequent suites use separate directories and source receipts.
