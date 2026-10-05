# Qwen vector context capacity ladder

This is a provisioning map for the reduced Qwen vector decode RTL. It records how the same parameterized core and timed physical-HBM K/V system are configured as the seeded context grows. Exact evidence is recorded separately for each source snapshot; the table is not a throughput, energy, or physical timing estimate.

| Context positions | Reducer `LV` | K/V tile bits `LOG_TW` | CROM required / provisioned words | VM minimum / provisioned FP32 elements | Logical K/V words | Physical 32-byte K/V sectors | BF16 window lines / data | Start lead, cycles | Exact timed-HBM token |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 512 | 5 | 5 | 5,889 / 8,192 | 7,680 / 8,192 | 8,192 | 4,096 | 1,024 / 128 KiB | 2,048 | [PASS](../results/rtl/hdc_qwen_context_512.json) |
| 1,024 | 6 | 6 | 9,985 / 16,384 | 11,776 / 16,384 | 16,384 | 8,192 | 2,048 / 256 KiB | 4,096 | [PASS](../results/rtl/hdc_qwen_context_1024.json) |
| 2,048 | 7 | 7 | 18,177 / 32,768 | 19,968 / 32,768 | 32,768 | 16,384 | 4,096 / 512 KiB | 8,192 | [PASS](../results/rtl/hdc_qwen_context_2048.json) |
| 8,192 | 9 | 9 | 67,329 / 131,072 | 69,120 / 131,072 | 131,072 | 65,536 | 16,384 / 2 MiB | 32,768 | Untested |

The CROM and VM requirements through 2,048 positions are measured from the generated ISA images. The 8,192-position row is derived from the same layout and awaits an exact RTL gate. The K/V image contains 16 logical 16-lane words per position; FP8 packing places two logical words in each physical HBM sector. The window holds four groups of 16 BF16 lanes per line, or 128 bytes per line. The displayed lead and window are conservative gate configurations, not measured minimums. Token cycles start after the 128-sector physical K-tail boot.

The current ISA has 16-bit count and 24-bit address fields, which can encode the 8K values above. The reducer's `LV` and the KV layout's `LOG_TW` are parameters. The 8K row is therefore an elaboration target, not evidence that the no-stall matrix/KV interface can sustain the full sequence. Each exact gate checks `consumer_line <= fetch_line` every cycle and compares the token, all logits, VM, KV, and committed physical HBM bytes against the ISA and independent arithmetic oracles. Consecutive-token behavior at 8K still needs separate K-tile close and V read-after-write coverage.
