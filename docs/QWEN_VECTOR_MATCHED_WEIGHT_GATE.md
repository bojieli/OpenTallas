# Qwen vector weight supply comparator: two-step checkpoint

The source-pinned [gate record](../results/rtl/hdc_qwen_vector_matched_weight_g4sw16.json) runs the same 104-instruction, 1,536-word-chunk program for both weight modes on `ot_hdc_core_vector_weight` at G4/SW16. Both modes use the autonomous physical HBM K-tail boot, banked K/V system, and the same timed four-pseudo-channel HBM model for KV. The HBM-weight mode adds `ot_hdc_wstream` as a second client of that controller; the ROM-weight mode leaves that client idle. The reduced checkpoint is two prompt steps at positions 0 and 1, not a generated-token or full-model rate study.

| Weight source | Exact output tokens | Core cycles, two steps | Pre-token K boot cycles | Logit / VM / KV / physical-byte / weight-word mismatches |
| --- | --- | ---: | ---: | --- |
| Synchronous ROM | 3978, 382 | 50,950 | 5,610 | 0 / 0 / 0 / 0 / 0 |
| Shared timed HBM | 3978, 382 | 53,592 | 5,610 | 0 / 0 / 0 / 0 / 0 |

The core-cycle difference is 2,642 cycles, or 5.19% of the ROM-mode two-step count, **in this reduced behavioral configuration only**. It includes weight admission and shared-HBM interference; it excludes pre-token K boot. It is not a shipped Qwen3 8B throughput or energy estimate. Both modes still move KV through off-chip HBM; ROM weight placement does not eliminate KV traffic.

The HBM-weight run accepted 41,787 weight read commands covering 167,156 physical 32-byte sectors. It observed 1,251 cycles waiting for the weight window, 149 cycles waiting for the embedding row, and 34 cycles in which a weight request was denied while sharing the port. The KV client accepted 176 read sectors and 16 writes in each mode; the second step read 16 V sectors written by the first. The boot performed 128 physical HBM sector reads before token timing began.

The HBM model has three distinct read events. It **accepts** sectors into per-channel queues, **schedules** a sector into a response queue (where its `st_rd` counter increments), and later **delivers** it through valid/ready. At the HBM-weight terminal check, 167,332 read sectors had been accepted, 167,140 scheduled, and 167,019 delivered. Thus 192 were queued but unscheduled and 121 scheduled responses were still in flight. These pending prefetch reads do not affect the completed token and must not be counted as delivered traffic or inferred energy. The gate checks accepted ≥ scheduled ≥ delivered, all delivered weight words against the ROM reference, every output and state snapshot, and every physically written KV byte.

The HBM timing parameters and one-cycle core clock are behavioral assumptions. This result establishes exact functional operation with modeled sharing and backpressure. It does not establish a physical memory bandwidth, ASIC timing closure, energy per token, or a GPU comparison. The full sequence below extends the same binary and oracle to all 16 prompt steps plus three generated steps.

## Full prompt and generation sequence

The [18-step source-pinned record](../results/rtl/hdc_qwen_vector_matched_weight_full_g4sw16.json) runs both cached executables concurrently with independent logs over all 16 prompt steps and three generated steps. All 18 output tokens match the ISA oracle in both modes, including generated tokens **1073, 382, 93**. Every step has zero token, logit, VM, and KV mismatch or fault; every physically written KV byte and every delivered weight word matches its reference. Both modes completed 128 K flush writes and 144 V reads from sectors written by earlier steps. The record pins 40 sources, 18 image files, the model checkpoint, and both executable hashes; the images and executable hashes equal the two-step checkpoint.

| Weight source | Summed 18 core cycles | Pre-token K boot cycles | KV HBM reads / writes | Weight HBM sectors accepted | Weight delivery errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| Synchronous ROM | 494,099 | 5,610 | 1,200 / 272 | 0 | 0 |
| Shared timed HBM | 521,782 | 5,610 | 1,200 / 272 | 1,477,976 | 0 |

The HBM-weight mode used 27,683 more simulated core cycles (5.60% of the ROM-mode count) in this **reduced behavioral model with this chunked program**. It experienced 3,978 weight-window wait cycles, 2,947 embedding wait cycles, and 506 weight-request denial cycles at the shared arbiter. These counters overlap in time and should not be summed as an explanation of the cycle delta. The HBM controller completed 1,200 KV read sectors in either mode. At the HBM-weight terminal boundary, it had accepted 1,479,176 read sectors in total, scheduled 1,478,982, and delivered 1,478,858. The outstanding 194 queued sectors and 124 scheduled responses are weight prefetch pipeline state, not completed token traffic.

Both modes use the same timed KV HBM path. The cycle comparison isolates weight source inside the tested vector controller and schedule; it does not measure Qwen3 8B production throughput, energy, or a physical ROM versus HBM chip. The model's four pseudo-channels, timing parameters, and weight-stream rate remain assumptions.

## Deliberate shared-HBM bandwidth stress

The [matched one-channel record](../results/rtl/hdc_qwen_vector_matched_weight_npc1_g4sw16.json) and [bandwidth comparison](../results/rtl/hdc_qwen_weight_bandwidth_bound_g4sw16.json) rerun the same two prompt steps with one timed pseudo-channel shared by KV and HBM weights. The four-channel record above is the reference. The source and 18 image hashes match between channel counts; within each count, the ROM and HBM arms use identical controller RTL, ISA, arithmetic, images, and KV-HBM traffic. Both counts produce tokens 3978 and 382 with zero token, logit, VM, KV, physical-byte, or delivered-weight mismatch.

| Shared pseudo-channels | ROM core cycles | HBM-weight core cycles | HBM / ROM | Completed weight sectors | Weight wait cycles |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 50,950 | 53,592 | 1.052× | 166,843 | 1,251 |
| 1 | 50,759 | 189,428 | 3.732× | 164,888 | 137,974 |

Both HBM arms consume exactly 40,960 weight words, or 5,242,880 useful bytes. Their completed physical-sector counts differ because the two channel counts leave different speculative prefetch tails at the two-step stop. At one channel, 164,888 sectors (5,276,416 bytes) complete in 189,428 core cycles: 0.870 sector per cycle, or 89.1% of the behavioral controller's 0.977-sector-per-cycle burst ceiling. The useful weight demand in the one-channel ROM schedule is 3.228 sectors per cycle, above that one-channel ceiling. The one-channel HBM arm is therefore weight-supply bound in this test. Its 137,974 weight wait cycles are observed counters; they should not be added to the 157 embedding wait cycles to explain the total cycle difference because the waits can overlap.

One pseudo-channel is deliberately just 1/256 of the modeled eight-stack package's channel count. This stress gate tests the shared controller's response to constrained weight supply; it is not a rate, power, energy, or bandwidth measurement for the adopted two-reticle INT8 Qwen package. The test uses reduced BF16-weight G4/SW16 arithmetic and two **prompt** steps. The full-shape INT8 HBM comparator has a separate code-word, scale, address-width, and physical-design gate.
