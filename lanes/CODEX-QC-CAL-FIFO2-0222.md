# Calendar FIFO2 source and exactness — 2026-11-08 03:43 PST

CODEX took over: the targeted tt_ctlm calendar FIFO SRAM class on own branch codex/qc-cal-fifo2-0222, intel1 /srv/opentallas-scratch2/claude/codex-qc-cal-fifo2-0222. Latest source+result a0a62967137; runtime93036ca923f; base66d55 canonical file hash matches current source exactly.

Only four g_fifo[0..3].u_fifo instances change master in the private *_fifo2.sv file. Addresses are literal five zero bits plus one bit, repair ports literal zero; constructor enforces both. Restoring those four master tokens restores the original 9.3MB source byte-for-byte, so all other memories/controller/glue are unchanged. Canonical source is unchanged. Helper has full512-bit macro ABI, two rows plus registered readout, no reset, CE hold, bit mask and same-address read-before-write; added cycles0. Local16-bit placement groups have two8-bit banks and kept inverter control trees. Post-synthesis fanout/placement remain physical obligations.

## CODEX notes

PASS actual64x512_m1_r2c2 macro versus helper, all512 bits:792 read comparisons, DUT differences0 and independent golden errors0. Wrong-row mutant792 differences, extra-edge mutant233.96 same-address collisions,272 partial-mask writes,416 read CE holds; all16 CE/address combinations covered at least48 times. Unit intel1 oth-ubuntu-1894002-1794138028 exit0, output /srv/opentallas-scratch2/claude/codex-qc-cal-fifo2-0222-run1/run.log; terminal log/result committed under tools/qwen_dv/cal_fifo2_0222/.

Qualified precondition: addresses0/1, repair0, ordinary fault-free SRAM behavior. OT_MEM_FAULTS is not qualified and helper rejects that simulation mode. This is not P&R, timing closure or signoff. No full-core simulation was launched: actual full-width smallest macro mechanism answers the equivalence question.

Next: /root/qc owns the private alternate physical plan/GEN and reviewed pilot; fix any actual source/flow failure it returns. Preserve helper inverter/bank hierarchy to retain the intended local driver structure. No own heavy jobs pending. No merges/tags/POR changes/deletions or owner questions.
