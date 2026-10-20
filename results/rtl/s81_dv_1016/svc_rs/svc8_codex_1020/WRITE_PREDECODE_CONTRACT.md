# Same-edge stationary-write predecode audit

The opt-in parameter `WRITE_PREDECODE` defaults to zero; `SVC8_WRITE_PREDECODE` selects its default to one for the standalone native/lockstep vehicle. Original arithmetic, score latency, bank skew, SRAM rings, reset landing, output registers, and ports are unchanged.

For input values present before edge e, the old group captures mode, valid, bank, group, data, and head ID at e. It updates stationary bank `ab` at e+1 from those captured values. The successor captures the data/bank at e and these predicates at the same e:

- normal: valid and not mode and group equals the 8-bit head ID;
- low: valid and mode and group equals this lane pair;
- high: valid and mode and w2v and group+1 equals this lane pair.

At e+1, normal writes the captured direct word, high writes captured pcol2, and low writes captured pcol. High retains the original priority. Low and high cannot both hold for one lane pair. No matching predicate means hold. An out-of-range bank means hold. Head ID remains truncated to eight bits before comparison; group+1 is evaluated with the same expression width/context as the original comparison. Invalid cycles hold state. Both versions clear their valid/write predicates on the same landed asynchronous reset; payload registers and stationary weights retain the original no-reset behavior. `gid` is static per production group (g=0..3); lockstep exercises gids 0/1/3.

There are no added score or write edges. Producer must still write stationary weights before first use. The source-reset contract remains rst_n asserted >=4 edges, with no iv/ld_v during reset or the first six release edges. The existing group lockstep releases reset at cycle4 and withholds live input through cycle12, while the landed-parent bench uses reset_cycles24. Neither fact alone proves every production producer observes the new group release contract.

The production tile currently instantiates `ot_hdc_v41x_attn_hgrp_s81` under `OT_ATTN_HGRP_HARD`. The landed-parent spec and mk_attw_lp.py also name that old source/view. Thus SOP2/SOLP2 receipts validate the original hard group and producer/consumer schedule; they do not by themselves validate adoption of hgrp8. After hgrp8 strict census/layout, integration must explicitly replace the child source/view and run the minimum parent/consumer proof with that actual replacement. TLX/TXD retain their existing values because the replacement is zero-cycle.

ST0 is not qualified: prod_s0 faults bit19 (0x00080000), the source's compiled P.V drain underflow check, while score and selection checks have zero errors. The bench compiles PVO=PO+8*ceil(T/32)+KPV; ST0 requires separate diagnosis/measurement before any drain constant change. ST2 production and release variants each have eight passing receipts. SOLPM2 is diagnostic until its ST0 baseline passes; SOLPM1 remains live. Do not promote either mutant witness as a qualified baseline/candidate pair yet.

The 17 ring macros hold long delays; each stationary lane holds an independently accessed 5x16-bit bank, below the 2kb indexed-storage threshold per array. Outline/fanout/reach and parent region clocks still require actual retained-netlist and physical checks; this audit grants no waiver.
