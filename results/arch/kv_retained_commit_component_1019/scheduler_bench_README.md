# Retained scheduler component checks

This is a private scheduler component experiment, not native health binding or a release calendar receipt. The final input hashes, fleet unit, case results and evidence archive are recorded in `scheduler_run_receipt.json`. The source is owned by the scheduler lane; this branch owns only the bench, runners and evidence.

The actual SU scheduler uses NSLOT=1, ENG_CTX=1, MODE=0, MU_OUT=0, NW=18, PLB=13 and FMT=1. The conditional component fixture has H=12 and response deadline D=8. The test drives real CSR writes, descriptor/prompt DMA responses, external synchronous prompt memory and an independent deterministic engine. There is no hierarchical force, deposit or state setup. Hierarchical `ev_n` reads only observe legal traffic capacity. `eng_start` is observed one edge after the scheduler's I_GO acceptance E0; the H check is at observed start +11 edges.

The health identity domain is **HOST_DESCRIPTOR_COMPONENT**: independently constructed zero-extended descriptor client tag16 in tag59, installation generation2, slot0 and validated engine position18. It is not the actual native TAG59 mapping. The mirror is checked at word-zero offer, before AW/W handshakes, and retained after later faults. DMA channel stability checks run on every stalled edge.

| Cases | Actually tested |
|---|---|
| 0 | Healthy generation; complete 64-bit CQ word0 `002b000012340025` and word1 `0000000100000003`; mirror, confirmed response, token/request counters1 |
| 1,5 | Prompt-time fault and deadline with late raw engine done; exactly one actual step-retire pulse; no committed mirror progress or success counters |
| 2,10,11 | Warm loss while both AW/W stall, only AW accepted, and only W accepted; channel data/address stability and retained ownership |
| 3,8 | Healthy two-token prompt; no mirror progress before H, first prompt mirror progress at H with DMA completely unavailable, then correct second engine position/result |
| 4,19,20 | Fault on, one edge before, and one edge after word-zero offer; immediate offered-word fault check before/on; paid mirror retained after offer |
| 6 | Two real descriptors and explicit true drain between them; correct new client tag/generation and two completions |
| 7 | Independently wrong health identity fails closed |
| 9 | Word-zero AW/W stall; mirror advances at offer before acceptance, then survives warm loss with stable offered channels |
| 12,13 | Actual error BRESP for CQ word1 and CQ word0; sticky poison and zero success counters; word-zero error cannot undo already offered mirror |
| 14,25 | Real configured MSI flow and MSI BRESP error following a healthy CQ; the already committed mirror and success counters survive later MSI error |
| 15 | Raw POR while a real engine request is owned clears owner, poison, pending interface state and mirror |
| 16,17,18 | Fault at H−1, H and H+1 for prompt completion; before/on H prevents progress, after H retains paid prompt progress |
| 21 | Forty-token legal request with CQ word1 stalled; actual traffic saturates at 14 queued events/14 issues; fault plus DMA release yields one fault completion, zero later successful word0, retained owner and remaining immutable queue |
| 22,23,24 | Conditional observed PLL-loss, execution-restart and role-fault input probes poison an owned request; selected analog PLL runtime-loss/real ingress reachability is not asserted |

Six causal mutants must fail their committed witness regex: word-zero cut bypass, missing deadline, health-gated raw done, missing warm-loss detection, identity-check bypass and success-counter regression. Four illegal opt-in configurations must fail `RC_COMPONENT_CONTRACT`: H=0, deadline>H, COMPONENT_FIXTURE=0 and NSLOT=4. A separate default-off dual-instance miter compares all **57 original output ports** against the unmodified original on one complete healthy trace, including CSR counter reads.

Still OPEN: actual native owner/health identity binding; production clocks, phase, H/deadline and full retirement plane; MU4; physical SRAM implementation, fanout/reset/timing closure; complete transaction-language/exhaustive interleaving proof; raw POR during every individual DMA phase; MSI payload/strobe exhaustive checking; and the descriptor-error enqueue race between I_IDLE margin and I_GO (the latest source guards real I_GO occupancy, but that exact race is not generated here). The legal-traffic 14-event observation is not a proof of every reachable queue state and does not claim the nominal16 entries were all filled. The default-off miter covers the recorded healthy trace, not all inputs.

Historical failed or weak-oracle evidence remains in the archive: an initial default miter omitted baseline clock/reset wiring; a reuse assertion sampled an observer after its valid pulse; the initial word-zero mutant escaped an end-state-only oracle because a later fault report overwrote the earlier success. The corrected oracle checks every actual CQ word0 immediately. Earlier source56faaf and2dfda results remain separate from the final source receipt.
