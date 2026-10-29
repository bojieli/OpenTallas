# KV native4 provider mapped-cell inventory

The actual 1139-stage provider synthesized to 10,159 physical cells: 4464 FFs and 5695 combinational cells, 1603.30428 um2. Every provisional FF-only row is too narrow for its complete mapped stage: actual one-row widths are 4.32–5.292 um versus provisional 3.24–4.32 um. This is a diagnostic inventory, not physical qualification.

Inputs and actual output files are on intel1 under `/srv/opentallas-scratch2/claude/codex-kv-provider-clock-1029/synth`. Inputs are native4 emitted RTL/manifest plus common RTL from `77f3ca517`; synth ran once in the pinned ASAP7 ORFS image via ot-run unit `oth-ubuntu-2212734-1793268842`.

Synthesis passed. The original collector failed because Yosys prepends an explicit `$flatten\\` instance prefix and retains `$scopeinfo` metadata. The corrected collector accepts those exact forms, excludes only metadata, and still rejects unknown hierarchy and physical masters. Every one of 157 external outputs is implemented as INVx1 after the same-stage FF QN. The inventory records both the actual final output driver and the launching FF, including the inverter cone. Wrong-stage and unowned-cell controls are caught.

`provider_cells_aliases.json` also exposes exact surviving named state aliases. Only 1139 of 4464 FFs retain a state name after optimization; the others remain unclassified. No roles are inferred from instance ordering. QC's generic placement owner consumes the actual cell inventory; further reset FFs need emitter-declared roles.

Physical work is held on the discovered global `rst_raw_n` star; KV owns bounded reset delivery. Actual all-cell placement, clock load, GRT RC, polarity-resolved readout, and CA qualification are pending. The existing native spine/row image was viewed as a conditional geometry review; it does not qualify these missing steps.

## Bounded-reset native6 successor

The named-reset source (7147152fc, real hub_C root) maps 1528 stages to 22,671 physical cells: 10,530 FFs and 12,141 combinational cells, 3670.85034 um2. The declared FF census matches every stage, including its reset count: 6029 origin FFs and 4501 reset FFs. All-cell one-row widths are 6.804–9.018 um. No virtual root is emitted in this vehicle, so the separately discovered virtual-root reset alias defect does not affect it.

The collector recognizes the explicit u_st/u_rst hierarchy and labels origin/reset ownership without inferring it from cell order. Postmap flattening clears module and instance keep_hierarchy attributes on all selected objects. A missing non-output FF control now fails the per-stage census even when output cones remain correct; this detects reset logic pruned after an undriven reset input. The fresh positive and all three controls pass (`native6_controls.json`). The synth unit is intel1 `oth-ubuntu-2417561-1793270064`; actual files are in the sibling `synth6` directory.

Physical qualification still requires the real partition boundary joins, actual origin-FF clock insertion below each entry, all-cell source DB and PG/clock load measurement. Real-origin common insertion cannot be canceled against a virtual stage clocked directly at a die clock node. This inventory makes no phase or route claim.
