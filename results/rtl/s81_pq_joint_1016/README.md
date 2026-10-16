# PQ joint control and lane source candidate

This packet is an explicit candidate, with no production manifest or default RTL change. `source_hierarchy.json` pins every actual input source and define. `extraction.json` records source grouping, the reversible projection of unused boundary bits, literal mapped calendar ROM identities, and the isolated AND/OR carry cone removed by Yosys. No state, consumed logic or macro is removed. The generated RTL is `rtl/dsrom_sys/s81_ph/pq/candidates/dsfd_sp_pq_joint_candidate.v`.

The joint control owns the actual command endpoint, calendar reader and two real calendar ROMs, CALCAP state and ROM4 selector. The lane owns actual lane state. The parent contains only the two new groups, 78 existing datapath hard-leaf instances and connecting wires. Existing source clocks and edges are preserved by extraction.

`physical_boundary_request.json` is an unassigned logical boundary: control has 1,901 total pin bits and three roots (8,321 command, 4,535 control, 950 calendar FF bits); lane has 3,838 pin bits and 2,204 lane FF bits. These are generic source counts, before mapping or pin-register cloning. They are not measured CTS or pin homes. Body, exact pin positions, macro placement, native timing, parent static calendar and full token qualification remain OPEN.

The explicit source flags include QB_PINREAD, CTL_CALCAP and AQ_SIDE_PARITY in addition to the current split configuration. PINREAD adds two read edges versus old headp and requires the second align leaf; CALCAP adds one control input edge. AQ_SIDE_PARITY uses the real AQ leaf registered parity output instead of parent recomputation from 512 data and 20 exponent wires, at the same parity edge. None is silently activated in the die.

`public_lockstep.json` compares all 2,778 public output bits for 668 active edges of the actual descriptor/calendar fixture, with all target leaves and mapped memory functional models. Four independent stop-clock mutants (control, lane, command, calendar) each produce a real public-pin mismatch. `public_positive.log` retains the pass marker. This proves source partition behavior in that fixture; it does not prove full numerical/token execution.

`aq_parity_positive.log` exercises actual full-shape AQ/QB/IX/BC component arithmetic, real storage models and the explicit side-parity candidate, passing four tests (5,857 baseline / 5,885 candidate cycles; 0.478060% diagnostic loss). `aq_parity_mutant.log` records an actual unexpected-fault failure at test 0 cycle 86 when the AQ parity is broken. This component diagnostic uses the legacy controller; `native_full_token_qualified=0` remains explicit.

Reproduce extraction with tools/s81/pq_control_extract.py using the recorded hierarchy; tools/s81/pq_joint_lockstep.py consumes the generated extraction directory, hierarchy and actual compiled calendar images. No RTL reference replacement, behavioral memory stand-in, timing waiver or fake parent view is claimed.
