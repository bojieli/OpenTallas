# Exact current histogram-child recovery

The 435-pin PIN_COPY cp1 child was already physically SIGNED. The nine actual view files are recovered byte-for-byte from 35cd6d73460; no rebuild or re-sign was performed. Current bank, Kogge-Stone helper and reset helper bytes equal the signed revision65902f47b3a. Fixed master parameters W16/CB11/BANK0/NB32/HPIPE1 match the current actual ot_s81ph_hq_hist parent.

The smallest current parent multicast vehicle is one 8-bank histogram. Its exact source conditionally drives 17 equal clr pins and sixteen equal four-bit gsel copies per bank. Scalar vs PIN_COPY parent lockstep PASS12000cycles,11671 full-output checks,320 reset edges,0 differences. A wrong gsel copy mutant caused3754 mismatch cycles. All data and output cycles are unchanged. Native source/module renames only distinguish the two elaborations; no arithmetic changes.

This qualifies the parent multicast mechanism and current-source correspondence to the archived master. It does not qualify the complete BKq parent, its clock, physical hierarchy or adoption. Those remain held, including the M3 parent clock.
