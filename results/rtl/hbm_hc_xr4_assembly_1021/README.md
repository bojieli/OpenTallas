# HC root xr4 assembly

Parallel parent assembly on the accepted k4 tail and P40 external root calendar. Source is preserved in this isolated sparse worktree. The existing xr3 specification already declares both programme and table SRAMs, repairing the old one-versus-two macro mismatch. The parent now needs two hard tail children and three SAFE mix SRAMs; the old xr3 source list and macro list cannot be reused unchanged. The committed interface-only tail stub supports native parent assembly and conveys no physical qualification. Actual k4 MAIN and fallback gates continue. Root latency is priced by TOKEN at tail +495 plus P40 read +16 and root +1.

Actual terminal scopes in memory_journal.log measured 517.4 MiB (plain synth/census) and 1.4 GiB (clone/retain/census). The unadmitted folded continuation was resized from24 GiB to8 GiB on this measured same-phase footprint; no source/shape change or live command restart. Prior source and failed outputs retained.
