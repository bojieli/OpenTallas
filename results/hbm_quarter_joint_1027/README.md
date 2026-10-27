# Native quarter joint FF planning

Source-model proposal only. The allocator reserves distinct ASAP7 row-grid sites for every modeled source FF and spare sites to keep each declared set at or below 60% fill. Hard HCOL/tail/SRAM bodies, clock islands and existing banks are excluded. All covered edges are recomputed at allocated centers. No RTL, cycles, physical plan or route changed.

The output-only 5,280 FF subset fits with 6,336 covered hops and max 396.502 um. Combining the final3 control graph required directional repair of 13 tight input-control FF placements: the conservative half-slack envelope alone rejected feasible sites. The wider 1.404 x 0.27 um allocation fits 18,692 modeled FFs, all 24,039 hops, max 404.838 um; image was inspected. Initial envelope failures and immutable failed runs remain in the artifact directory.

This is not mapped-cell authority. Source owner subsequently identified 6,150 md.line identities as semantic delay states implemented by ot_hdc_delay_rf, not literal pipeline FFs. Those identities must be replaced with actual RF cells and arcs before adopting native placement. Other mapped aliases may merge. Unmodeled FFs, real macro halos, PG, row orientation, clock/reset and hold remain outside this planning subset.

Run helper with --directional-repair and the corrected final3 control graph. Its PASS_SUBSET_MODEL verdict deliberately does not authorize route or G1 acceptance.

## Actual RF replacement

The followup replaces all 6,150 semantic md.line identities with 6,164 actual bare-mapped RF FFs. Exact-master row allocation includes all 22,978 RF standard cells, including combinational logic. Each engine uses 1,601.1027 um2 in its 76 x 76 um box (27.72% fill). The second bank moves north to avoid the score/control street. Both boxes are reserved before jointly repacking the remaining 12,542 source FFs. All 78,881 combined sequential arcs have actual allocated endpoints, zero missing or over-405 hops; max 404.838 um. Full cells and immutable inputs remain in the artifact directory recorded in actual_rf_joint_summary.json. The plotted yellow RF rectangles reserve every packed RF cell; green dots show surrounding movable source FFs.

RF D-cone extraction covers all pointer feedback and write/read mux predecessors, 25 external data inputs per engine, and actual registered dout outputs to score. The existing native RF intentionally does not reset its data/pointer state; rst_n is an unused port. No reset exception or source change was introduced. Ordinary source alias merges and all native cells outside this subset remain unresolved; this is a mixed source/bare-mapped RF planning result, not physical signoff or route authority.

## Bare mapped alias diagnostic

Canonicalizing the 7,111 resolved source IDs merges 52 register groups (48 have conflicting original coordinates), eliminating 84 duplicate FF placements. Each group is placed in the exact intersection of every fanin/fanout 405-um diamond, outside hard/RF/clock/bank and existing cell/spare reservations; one additional spare row site keeps each new one-FF group at 50% fill. All 52 groups fit; their worst incident hop is 404.062 um. The canonical combined graph has 72,813 distinct arcs, zero missing or over-405 hops, max 404.838 um. No merged groups have direct mutual edges, so these local merge decisions are independent.

This remains a bare-map diagnostic. There are 151 unresolved non-md source identities: 128 core.rdy2, eight ready2, eight ofl, four settle, two online_q and one ov. The actual preservation-enabled quarter synthesis must resolve those identities and supersede these bare aliases; output-data FF aliases and all unmodeled storage still need mapping. Exact merge locations and all unresolved IDs are in bare_alias_diagnostic.json; original allocated cells and combined graph remain in the immutable runtime directory.
