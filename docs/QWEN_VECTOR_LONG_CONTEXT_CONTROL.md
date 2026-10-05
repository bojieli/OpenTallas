# Qwen vector context-256 exactness control

The source-pinned [control record](../results/rtl/hdc_qwen_long_context_256_control.json)
seeds 255 prompt positions into the reduced Qwen3 vector core's FP8 KV image,
then executes position 255 through the G4/SW16 vector ISA and a four-pseudo-channel
timed behavioral HBM model. An independent arithmetic oracle and the ISA model
both predict token 1561. The RTL produced token 1561 with zero logit, VM, KV,
fault, and committed physical HBM byte mismatches. The pre-token K-tail boot
read 128 physical 32-byte sectors. The token made 2,952 KV HBM read requests
and eight KV writes, all eight committed before physical readback. The core
used 192,856 cycles; this excludes the pre-token boot interval.

The HBM model recorded 815 ACT commands and 188 refreshes, but **zero request
backpressure cycles**. The testbench printed `FAIL` solely because this first
campaign required a nonzero backpressure count. The record labels its exactness
control as passed and the queue-pressure target as unmet, preserving that raw
harness output. It must not be cited as evidence that the KV path survives
queue-pressure stalls. A separate tagged competing-read campaign will test
that condition.

This is a reduced model with behavioral HBM timing. The present vector
reducer has four temporal levels and supports at most 16 width-16 vectors,
or 256 score elements in one softmax segment. An 8K exact token needs a
redesigned chunked reduction and larger address, VM, and KV geometry.
This control makes no production bandwidth, throughput, energy, or physical
timing claim.
