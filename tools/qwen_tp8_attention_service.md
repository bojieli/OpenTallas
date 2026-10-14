# Native fused TP8 attention service candidate

`ot_qwen_tp8_attention_service` connects lossless FP32 Q transport to the actual native H score/exp/Z body, its actual synchronous BF16 exponent memories, physical-stack V row response transport, the two canonical PV256 residue-pair trees, and the 32 independent final joins with the actual reciprocal. The harness never supplies an exponent or a reciprocal.

This is an explicit candidate source profile: compile with `KVD_HEADS=1`, `KVD_Q_FP32=1`, `KVD_QK_ONLY=1`, and `KVD_ECTL3`. Those macros default to the legacy profile when absent. New profile sources and common-clock functional adaptation have no inherited CLOSED physical qualification. The ordinary H body retains its complete K/V behavior with `KVD_QK_ONLY=0`; only the native profile ends its request generator and row consumer after K group0.

The descriptor is `{epoch[15:0], layer[5:0], position[17:0]}` with position <=8191 and context = position+1. `fused_program_capability` must come from a source-bound semantic-lowering validator; the original unfused image cannot assert it. The actual weight emitter can add required BF16 post-collective scales, so capability is independent of literal program word count. Q arrives as 32 ascending 512-bit FP32 beats; BF16 RNE conversion occurs in H at actual consumption.

K requests have 32 ordered engine queues (four stacks, eight engines). Each finite request adapter retains 128 entries, equal to H's DQ credit limit, through response retirement. External request stalls never pretend H has request-ready. K responses carry t, epoch, and layer; invalid tags, reordering, unsolicited responses, wrong type, or overruns cause a fault. V uses eight owned slots per canonical pair, with request stack selection derived from t[8:7]. Actual V data and tags are registered together with an actual exponent SRAM read for k=t[12:9], residue=t[6:0].

Results are 32 ascending registered 512-bit FP32 beats. A producer holds each beat under backpressure. `result_done` records only acceptance of beat31. It does not mean that vector memory committed any result. Native dispatch must wait for the separately observed 32 VM commit acknowledgements before dependent O projection or token completion. The service waits for finalizer release before accepting the next descriptor, and requires fresh score-phase clearing before admitting its V phase.

The functional harness uses actual Q/K/V input rows and canonical golden outputs. The full-width build uses the existing simulation-only FP32 add/multiply and fast-FP DPI stand-ins with their RTL latency/valid pipelines; it exercises the actual H/SFU/control/transport/SRAM/tree ordering rather than compiling every bit-level FPU instance. This is functional arithmetic evidence with that explicit substitution, and does not prove every full-width bit-level FPU instance or any physical timing. Its response model has a synthetic latency and intentionally does not qualify HBM bandwidth, physical routing, clock trees, workload rates, or a full token. The common-clock adapter also does not qualify the independent clock entries' delivery.

Build/run only under measured `ot-run` admission (measured full-width peak 30.6 GiB, current request 48 GB and eight build threads). The build uses `-O1` for C++ compilation; this avoids the very long compilation of the initial `-Os` unity objects:

```
bash tools/qwen_tp8_attention_service_build.sh obj
python3 tools/qwen_tp8_attention_native.py vectors --ctx 8192 --seed 1 --kind normal --groups 3072 --out vectors/full
obj/Vtb vectors/full steady
obj/Vtb vectors/full stalls
obj/Vtb vectors/full restart vectors/different_frame
```

The optional second directory in restart mode must contain an independently generated frame to test actual stale-state protection. The small-context PV implementation explicitly clears all 128 retained residues before each frame, adding 128 initialization edges; its operator proof alone does not qualify the composed small-context service. Live source archives are immutable, and the initial full8192 build used the pre-small-context version; subsequent suites use separate directories and source receipts.

The `593c88424` integrated suite passed single-frame arithmetic but failed a different-input 8192-to-1 restart without reset (500 second-frame word errors, no hardware fault). A read-only trace of the same DUT showed that empty stacks could emit retained local maxima before their child controllers cleared their previous flags. The native successor gates the maximum's presence bit by actual stack token ownership (`n_s != 0`). Resetting between frames would hide this defect and cannot qualify reuse across layers.

The corrected `f46073090` RTL, including the registered result interface, has its own [source/binary/vector-bound component receipt](qwen_tp8_attention_service_evidence/service_f46073090.json): 37 positive cases, 47 frames and 24,064 bit-exact FP32 outputs, including ten consecutive-frame cases without reset; all seven mutants are detected. Full8192 steady and stalled runs take 11,955 and 13,146 functional fixture cycles. The previously failing 8192-to-1 restart passes all 1,024 outputs. Checkpoint-derived consecutive layer payloads also pass at context256; the component uses descriptor tags6/7, preloaded K/V, and oracle-fed previous-layer X, so actual mapped layer0/1 storage and RTL layer carry require the composed harness.

The original main command completed all 27 numerical cases, then exited2 because its later vector-generation argument `--kind ties` was invalid. That configuration failure is preserved in the receipt. The separate corrected run uses `--kind precision_ties`, completes the omitted midpoint and mutant tests against the same binary, and exits0. The additional no-reset suite also exits0. These receipts establish functional component behavior with the stated simulation substitutions; physical, bandwidth, rate, VM-commit and full-layer/token qualification remain open.

For one frame, the functional service accepts context-length K rows and context-length V rows, each containing 128 useful bytes. At context 8192 that is 2,097,152 useful read bytes and 32 output beats containing 2,048 FP32 result bytes. Those are logical payload counts. The external read assembler must separately account for the actual mapped 32-byte sectors, controller requests, and physical traffic; the functional latency model establishes none of those timing or bandwidth costs.

`tb_qwen_tp8_k_request_adapter.cpp` independently exercises all 128 retained requests across a 1000-cycle external request stall, overlapping ordered request/response retirement, and a fresh frame. Its fault cases cover a 129th request, a busy restart, unsolicited response, wrong token order, epoch, layer, and request type. A temporary capacity-127 source mutant must fail the capacity test. This is adapter mechanism evidence; the composed H service still needs its own proofs.
