# Qwen vector tokens 254–255 with physical HBM K/V

The source-pinned [RTL record](../results/rtl/hdc_qwen_long_two_254_255.json)
seeds 254 positions from the reduced Qwen3 arithmetic golden model, then
executes two consecutive G4/SW16 vector tokens at positions 254 and 255.
Both positions produce token **1561**. The testbench compares all 4,096
logits, 8,192 VM elements, and 65,536 KV elements after **each** token;
both comparisons have zero mismatches and zero core or KV-system faults.

The same four-pseudo-channel timed behavioral HBM model supplies physical
32-byte FP8 K/V sectors throughout. Autonomous K-tail boot reads 128 sectors.
Across the two tokens and subsequent maintenance action, the system accepts
5,904 read sectors and 144 write transactions; all 144 writes commit. During
position 255 it reads 16 V sectors written before that token. The final
physical byte comparison has zero mismatches.

The two tokens take 192,856 and 194,998 core cycles, respectively. These
counts exclude pre-token K-tail boot and the following maintenance action.
The HBM model records 1,663 ACT commands and 408 refreshes, with zero
request backpressure cycles in this particular run.

The K streamer closes a 16-position tile when the **next** tile starts.
Positions 254 and 255 therefore leave tile 15 resident. After both core
tokens finish, the testbench sends a position-256 `tok_start` pulse only to
the KV system to close tile 15. No third core token is executed. The close
produces 128 K write transactions across 64 packed sectors; all 64 sectors
match the final golden K bytes, and the writes are included in the 144
committed transactions above. The source-pinned record reports this pulse
separately from token execution.

This is a reduced-model functional and behavioral HBM timing gate at the
current 256-element vector reducer ceiling. It does not establish an 8K
context, sustained contention tolerance, calibrated production bandwidth,
throughput, energy, or physical timing.
