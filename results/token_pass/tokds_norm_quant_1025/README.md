# Norm payload compiler, 2026-10-25

Reference construction PASS for L0/L2/L14/L20: 80 XQ payloads and 80 XB payloads per layer; rstd, 5,120 scaled BF16 values, 5,120 E4M3 values and 160 signed block exponents reproduce fixtures exactly. H/pre and checkpoint norm gains are producers. L14 first reconstructs genuine Engram checkpoint rows and full wkv through entry_engram; operation outputs are assertion targets only. This is reference/compiler evidence, not an RTL token pass.

Found and fixed an arithmetic contract bug: the layer/head compiler's XFIN_GO epsilon was 1e-6 (0x358637bd), whereas the released config requires 1e-20 (0x1e3ce508). The old-epsilon control differs on all four layer rstd values.

Wire encodings follow the actual vq/rstop ABI: XQ two 32-code blocks with signed 10-bit exponents; XB 64 BF16 values; 21-bit headers, 4 x 276-bit V fragments, source-SID rewrite after V assembly, full-width line forwarding. emit() refuses duplicate output slots and own/assembled collisions. Full16 quant schedule remains open; the initial autonomous trains collide on607 line edges /1,556 beats plus22 own/assembled edges.

Timing calibration from fully reclocked pre-deskew r4all cuts: root-writeback -> first own XQ line word145 cycles (0S548->693, 0N549->694, 7S549->694). V fragment0 leaves4 cycles before the complete own line word. Full-cut confirmation on deskew RTL is pending inherited builds.

norm_phase.py extracts the entry/CTL/NX mechanism without later quant or layer operations. Its records explicitly state full_layer=false; it never qualifies a complete token. NX_AFTER_LAST_NORMR remains138: the old faulting serializer restarted on each staggered leaf, so its final pass already began at leaf4, and another4 edges after the last command would double count the stagger. Actual deskew-cut confirmation is pending.
