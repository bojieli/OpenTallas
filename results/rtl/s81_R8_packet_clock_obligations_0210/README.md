# Conditional clock+transport obligations for current R8 packet inputs

The selected native counterexample5c86a737d stays scoped to its explicit common-clock/startup mapping. It identifies a missing coherent clock+transport relation, not a bad table or a replacement native contract. Current100 unqualified input groups include28 frame packet-input groups. Every one has different metadata ages at sinkbits1/567, while each current bound pair has equal ages.24 originate at slice parents and4 at prior frame forwarders. Actual source/sink bit ranges are preserved, not inferred lane aliases. Only the selected0L01 literal source-valid duplication and native failure are proven here; the other27 are conditional obligations, not qualified cases.

For duplicate source-valid bits, necessary consumer alignment is:

`transport_age[1] + C[1] == transport_age[567] + C[567]`.

`C` is the net integer-edge effect of the actual source and forwarded-clock epochs, landing read mapping/K, reset/startup relation and final consumer sampling relative to the metadata count. These are quantities to extract/qualify from the coherent physical/native producer and landing contract, not independently tunable offsets. They remain null here. The selected age46/45 recipe therefore needs C[1]−C[567]=−1; the uniform41 recipe needs zero. Our common-phase native vehicle supplies the latter mapping and rejects the former plain-delay application. Physical clock phases/reset epochs were not reconstructed by the diagnostic.

packet_clock_constraints.json emits the exact per-group conditional equalities and source/bit mappings. It does not choose a phase correction, landingK, reset epoch, pad, clock trim or larger buffer; it adds no rule. Actual count-aligned source/reset/clock legality and payload readiness remain required. Other72 input groups and13 replica relations remain open under their own existing contracts; source aliases or numerical match cannot waive them. GlobalR8/provider/cohort flags are unchanged.

This narrows the next work to exact producer aliases and built clock/reset/landing sample relations, rather than28 copies of the selected arithmetic build or blind age padding. No new RTL, simulation, plan, CAD, model latency or physical adoption occurred for this classification.
