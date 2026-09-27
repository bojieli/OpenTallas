# Qwen vector weight supply comparator: two-step checkpoint

The source-pinned [gate record](../results/rtl/hdc_qwen_vector_matched_weight_g4sw16.json) runs the same 104-instruction, 1,536-word-chunk program for both weight modes on `ot_hdc_core_vector_weight` at G4/SW16. Both modes use the autonomous physical HBM K-tail boot, banked K/V system, and the same timed four-pseudo-channel HBM model for KV. The HBM-weight mode adds `ot_hdc_wstream` as a second client of that controller; the ROM-weight mode leaves that client idle. The reduced checkpoint is two prompt steps at positions 0 and 1, not a generated-token or full-model rate study.

| Weight source | Exact output tokens | Core cycles, two steps | Pre-token K boot cycles | Logit / VM / KV / physical-byte / weight-word mismatches |
| --- | --- | ---: | ---: | --- |
| Synchronous ROM | 3978, 382 | 50,950 | 5,610 | 0 / 0 / 0 / 0 / 0 |
| Shared timed HBM | 3978, 382 | 53,592 | 5,610 | 0 / 0 / 0 / 0 / 0 |

The core-cycle difference is 2,642 cycles, or 5.19% of the ROM-mode two-step count, **in this reduced behavioral configuration only**. It includes weight admission and shared-HBM interference; it excludes pre-token K boot. It is not a shipped Qwen3 8B throughput or energy estimate. Both modes still move KV through off-chip HBM; ROM weight placement does not eliminate KV traffic.

The HBM-weight run accepted 41,787 weight read commands covering 167,156 physical 32-byte sectors. It observed 1,251 cycles waiting for the weight window, 149 cycles waiting for the embedding row, and 34 cycles in which a weight request was denied while sharing the port. The KV client accepted 176 read sectors and 16 writes in each mode; the second step read 16 V sectors written by the first. The boot performed 128 physical HBM sector reads before token timing began.

The HBM model has three distinct read events. It **accepts** sectors into per-channel queues, **schedules** a sector into a response queue (where its `st_rd` counter increments), and later **delivers** it through valid/ready. At the HBM-weight terminal check, 167,332 read sectors had been accepted, 167,140 scheduled, and 167,019 delivered. Thus 192 were queued but unscheduled and 121 scheduled responses were still in flight. These pending prefetch reads do not affect the completed token and must not be counted as delivered traffic or inferred energy. The gate checks accepted ≥ scheduled ≥ delivered, all delivered weight words against the ROM reference, every output and state snapshot, and every physically written KV byte.

The HBM timing parameters and one-cycle core clock are behavioral assumptions. This result establishes exact functional operation with modeled sharing and backpressure. It does not establish a physical memory bandwidth, ASIC timing closure, energy per token, or a GPU comparison. The next gate extends the same binary and oracle to all 16 prompt steps plus three generated steps.
