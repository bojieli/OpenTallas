# S81 native embedding expansion, 2026-10-15

Real released BF16 table rows for token 21946 (MTP0 main token), 128799
(DSpark noise), and original 1M input token 16754 pass the actual ROM bank
reader -> two mapped SRAM macro functional models -> RTL transpose ->
four-copy BF16 expansion -> registered VM and hop ports composition.
Each run emits exactly 640 VM rows and header + 640 HIDDEN flits in exactly
1365 cycles, with no fault and no ready/credit ports. Each copy-corruption
mutant fails with 1280 scoreboard errors. All 641 output lines are archived;
record.json pins the RTL/macro source hashes and the output hash.

The full-vocabulary fixed-slot issuer separately checks six boundary tokens
including token 12 (crosses a 4096-word leaf boundary), owner boundaries and
last vocabulary token 129279. All 320 addresses reconstruct token*320+word;
corrupt return macro identity faults. This is issuer-component evidence, not
an integrated full-table ROM fabric test.

Physical status: contract slot reserved by S-DIE, not routed. 216x216 um;
two 174.096x29.700 um SRAM masters, 81920 used data bits / 131072 physical bits,
2048b transpose staging. Exact compiler calendar is in the contract.

Remaining requirements: bind actual source-die role/engine, assigned pins,
TT setup/FF hold/DRC0, physical memory flight and VM/hop consumer composition,
full-vocabulary resident bank fabric. The selected-bank wrapper intentionally
rejects cross-bank rows; the full-table issuer supports them and requires the
real fixed-latency bank fabric. Neither fixture personalization nor the
issuer's response harness establishes that the entire resident table has been
instantiated. This closes the Python four-copy/transpose/framing computation
at this component boundary, not full native token qualification or throughput.
