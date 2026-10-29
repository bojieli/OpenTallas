# KV native4 provider mapped-cell inventory

The actual 1139-stage provider synthesized to 10,159 physical cells: 4464 FFs and 5695 combinational cells, 1603.30428 um2. Every provisional FF-only row is too narrow for its complete mapped stage: actual one-row widths are 4.32–5.292 um versus provisional 3.24–4.32 um. This is a diagnostic inventory, not physical qualification.

Inputs and actual output files are on intel1 under `/srv/opentallas-scratch2/claude/codex-kv-provider-clock-1029/synth`. Inputs are native4 emitted RTL/manifest plus common RTL from `77f3ca517`; synth ran once in the pinned ASAP7 ORFS image via ot-run unit `oth-ubuntu-2212734-1793268842`.

Synthesis passed. The original collector failed because Yosys prepends an explicit `$flatten\\` instance prefix and retains `$scopeinfo` metadata. The corrected collector accepts those exact forms, excludes only metadata, and still rejects unknown hierarchy and physical masters. Every one of 157 external outputs is implemented as INVx1 after the same-stage FF QN. The inventory records both the actual final output driver and the launching FF, including the inverter cone. Wrong-stage and unowned-cell controls are caught.

`provider_cells_aliases.json` also exposes exact surviving named state aliases. Only 1139 of 4464 FFs retain a state name after optimization; the others remain unclassified. No roles are inferred from instance ordering. QC's generic placement owner consumes the actual cell inventory; further reset FFs need emitter-declared roles.

Physical work is held on the discovered global `rst_raw_n` star; KV owns bounded reset delivery. Actual all-cell placement, clock load, GRT RC, polarity-resolved readout, and CA qualification are pending. The existing native spine/row image was viewed as a conditional geometry review; it does not qualify these missing steps.
