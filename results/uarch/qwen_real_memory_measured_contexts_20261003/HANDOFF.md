# Matched measured REAL_MEM contexts

P0/P255/P1023 each contain E and L0..L2 exact four-die outputs, plus exact actual REAL_MEM KV writeback. All six raw receipts share the same46source pins and binary. Each ideal/real pair additionally matches generated core, stage images, KV history, oracle, design and wire identities. The previous b4c331a72 matched-pair verifier is archived byte-identically and hash-checked; no dependency on an external worktree is required. Its older build() is not called.

The measured P1023 ideal layers each cost4940cycles. Actual REAL_MEM costs5789/7171/7027cycles. Deltas849/2231/2087 equal17.1862348178/45.1619433198/42.2469635628percent, using actual ideal denominators. Functional CLK_PS833 converts those deltas to0.707217/1.858423/1.738471us only. P0/P255 values remain exact. All nine observed layers span3.2472939217–45.1619433198percent. Layer-sum deltas are1632/1614/5167cycles at P0/P255/P1023.

This is actual three-layer service calibration at three positions, not a36-layer or8K full-token measurement. No percentage extrapolation, summation of overlapping stall counters, duplicate KV-delivery charge, posted-write gain, SS/FF clock credit or token-rate headline is supplied. Historical records, S82 tool/model/unified entrypoint, rejectedHA2 and excludedHA3 are untouched.

Replay:

```
python3 tools/qwen_real_memory_measured_contexts.py --verify
python3 -m pytest -q tests/test_qwen_real_memory_measured_contexts.py
```

7testsPASS, exact generated record replay, and every raw input byte matches the committed main source collection. No payload/checkpoint reads, inference, RTL builds or simulation runs were performed. This added-only milestone uses committed main8c6d5bd75 inputs and is disjoint from the S82 intake. Parent owns publication and calendar composition under matching service identities.
