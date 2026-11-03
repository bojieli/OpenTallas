# HBM spill allocation: 64-word VM/HBM-home congruence (four-stack ruling A; TOK-HBM-1 -> TOK-HBM-2, 2026-11-02)

Opt-in `vm_canonical_stream.py --vm-align 64`. The default (8) gives byte-identical output.
- `vm_value_phase.build(align=)`: every retired value-phase VM range is placed congruent with its canonical source
  word mod `align` (TOK-HBM-1).
- `vm_expert_entry.layout/lower(align=)`: NEW (TOK-HBM-2). The expert regions were packed densely at 32-word
  granularity, so 58 expert retirement stores (4.0M words, offset 32 mod 64) stayed non-congruent and staged every
  fragment. Each region base now pads to `(lo - base) % align`, which costs at most 32 words per region.
- `vm_value_phase.build`: NEW (TOK-HBM-2, only when align != 8). The per-row objects of one explicit-row record
  operand first try their placed sibling's source->VM translation. This keeps the uniform row stride, so the
  record stays folded. Without the hint, congruence padding scalarized 3-row records (+1,076 body commands).
- `results/tok_hbm_1030/check_canonical.py`: re-derives the expert lowering with the packet's
  `vm_hbm_congruence_words`.

Runs (epyc2, image candidate_mtp_N6_a122 = one N6 MTP_VERIFY step; `runs.json`):

| | align 8 (default) | align 64 |
|---|---|---|
| cached stream sha | 79a81185 (= reference, byte-identical) | cd7ee521 |
| check_canonical (20,842 address checks + 4 mutant controls) | PASS | PASS |
| max VM words (cap 261,120 below scratch) | 255,168 | 255,232 (+64) |
| cached commands: body / load / store | 8,477 / 12,528 / 12,155 | 8,981 / 12,853 / 12,222 |
| non-congruent stores | 7,345 (14.76M words) | 0 |
| staged fragments / words | 33,348 / 13.96M | 7,287 / 0.96M |
| staged without a local SU source (SID0/1) | 25,130 | 6,654 |

The 7,287 fragments still staged are head fragments only: stores whose HBM home is 8-word aligned but not 64-word
aligned, where both ends are misaligned. Removing them needs a 64-word pad of the HBM backing homes (a backing-layout
change; it would grow the reservation, ~0.3 MB estimated by TOK-HBM-1) or the runtime staging path. That path still
lacks the VM bank-changing copy.

Remaining cost of align 64: +504 body commands per step (6 %). These are mostly 3-row SU VOP records on 8-word
per-row scalars, which other 64-congruent objects crowd out of a shared translation. There are also +325 loads and
+67 stores in the cached stream, while load words drop. The per-command issue cost was not measured (UNVERIFIED);
next to the 13.0M staged words that are removed, it is expected to be small.
