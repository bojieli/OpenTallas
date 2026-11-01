Exact opt-in RED registered-pin specialization

The real standalone RED has207,508 standard cells and only343/352 private registered data pins. Eight l_ov input bits directly load33 reset-distinct capture flops; rd_v also feeds internal logic. Those existing reset signatures cannot be merged.

HARD_PINREG defaults to0. At1, eight unreset flops capture l_ov once. Each existing async-reset flop instead captures1 and its state masks the shared same-edge captured data. The original per-flop clock and reset nets remain unchanged. The existing rd_v output driver is duplicated with identical D/clock/reset for a private output. The data and reset release edges and all354 public interface bits remain unchanged. No arithmetic changes.

Proof covers the exact33 changed source-cell mappings. The Boolean clock transition is R?D:0 == D&(R?1:0). Under the existing state invariant Q=shared&flag, any asynchronous reset-fall subset preserves equality because both original Q and flag clear; reset rises leave both state values unchanged. Boot establishes original Q=flag=0 with arbitrary shared data. Both universal transition obligations pass SAT, as does the actual helper-source5-edge boot/reset cone. Wrong-mask and reset-bypass mutants produce counterexamples. The private rd_v clone has the exact existing D, clock and reset, so the same boot/transition identity applies.

Actual HARD_PINREG=1 standalone mapped synthesis/import completed:207,601 standard cells,27,077.2um²; measured cost+93 mapped cells/+10.1um². Actual face guard PASS352/352. The model charges9 added clock sinks and33 AND operations, with no absolute power claim before real cell/load timing.

The generated276.48um square standalone prototype has354 typed pins, M2–M5 routing,37.75% estimated core fill, and legal S-face clock/reset entries. The initial interior-clock draft was correctly refused without a master island; its failure is preserved. Sparse-only bundle failures were resolved by staging their exact repository dependencies. Clock350TT/283.5FF is a planned estimate only, not a signed arrival contract. Render was viewed; independent review and actual PLACE/CTS/GRT remain pending.

Parent adoption is separate. The measured eligible-five-cut SU-C parent still has433,951 cells. Cutting RED can bring its glue below400k, but exact parent resynthesis and a truthful registered-hop/physical relocation event are required. No parent over400k is routed, and this packet does not adopt any RED or recovered memory macro view.
