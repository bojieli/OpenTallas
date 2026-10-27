# Native quarter joint FF planning

Source-model proposal only. The allocator reserves distinct ASAP7 row-grid sites for every modeled source FF and spare sites to keep each declared set at or below 60% fill. Hard HCOL/tail/SRAM bodies, clock islands and existing banks are excluded. All covered edges are recomputed at allocated centers. No RTL, cycles, physical plan or route changed.

The output-only 5,280 FF subset fits with 6,336 covered hops and max 396.502 um. Combining the final3 control graph required directional repair of 13 tight input-control FF placements: the conservative half-slack envelope alone rejected feasible sites. The wider 1.404 x 0.27 um allocation fits 18,692 modeled FFs, all 24,039 hops, max 404.838 um; image was inspected. Initial envelope failures and immutable failed runs remain in the artifact directory.

This is not mapped-cell authority. Source owner subsequently identified 6,150 md.line identities as semantic delay states implemented by ot_hdc_delay_rf, not literal pipeline FFs. Those identities must be replaced with actual RF cells and arcs before adopting native placement. Other mapped aliases may merge. Unmodeled FFs, real macro halos, PG, row orientation, clock/reset and hold remain outside this planning subset.

Run helper with --directional-repair and the corrected final3 control graph. Its PASS_SUBSET_MODEL verdict deliberately does not authorize route or G1 acceptance.
