# Current bound control compiler and native HOST provider

This packet is based on main 8a121b0c8. It contains the real compiler, its CLI hook,
exact selected-source resolution, local timing vehicles and original timing
receipts. Main's newer `BoundDie` is retained. No physical plan or production RTL
is changed, and no historical die tree or transport/seqhost defaults are used.

The measured source pin-event ages are seqhost KS→accept4, KS→age0command5,
calendar command→north7/south8/CW3, and BK3. Atomic ring stages are2 and XRT
stages3; actual inter-unit routes come from the current strict-bound per-bit
`bind_sinks` graph. All53 measured functional dependencies match main byte for
byte. The original reset/KS phase receipt is explicit because the merged local
stage receipt does not contain that top-level clock metadata.

`tools/s81_dv/layer_prog/run_bound_native_boot.sh` is the actual compiler entry:
set BOUND, INVENTORY, ENTRY_PROGRAM, ENTRY_ROWS and fresh OUT; SOURCE_ROOT defaults
to this checkout and must include the exact manifest-selected RTL. Large canonical
bound files and native fixture records remain on intel1 under:

* `/srv/opentallas-scratch2/claude/tok-ds/s81_877/v2/out`
* `/srv/opentallas-scratch2/claude/codex-bound-inventory-1026/inventory.ext.json`
* `/srv/opentallas-scratch2/claude/codex-tok-ds-1026/bound_entry_norm.json`
* `/srv/opentallas-scratch2/claude/codex-tok-ds-1026/bound_entry_rows.json`

The current control record retains the inherited failed8-edge NORMR spacing.
The opt-in proposed retime uses actual PDSK, preserves every GO issue date and the
48-slot span per tier, and keeps GO≥8 after each slice's final NORMR. Passing
command spacing is not executed NORMR/GO or readiness qualification.

Concrete outputs are `boot_norm/native_commands.unsealed.host_boot.memh` (96rows,
96templates,385HOSTwords) and31 `boot_entry/entry_templates_*.unsealed.host_boot.memh`
files (3920 actual entry payloads;128templates/table except final80). Every515-bit
word is decoded back to its native PW/template input, and a payload mutant is
required to fail. CSR spacing5 is locally measured;1925/19600 word reservation
edges are loader costs, not global token timing or a target5 ACK calendar.

No calendar stage/start_phase, MU gap/RL/windows, external host/reset dates,
residency/readiness, KIT or END are inferred. Missing programme data stays in
explicit holds. No BEGIN is emitted without actual stage/phase. No SEAL is
emitted. The output status is UNSEALED_PROTOTYPE, never full-token PASS.

Actual compiler integration at d3f77920d4 completed through ot-run unit2454353 on
intel1 with exit0:16/16 exact control paths,0 blocked,96 commands; emitted385+
3920 exact HOST words with both payload mutants caught. The inherited spacing
FAIL and proposed current-PDSK spacing PASS are both retained. `integration.json`
is a compact receipt; full runtime records and concrete outputs remain at
`intel1:/srv/opentallas-scratch2/claude/native-control-1026/main_boot1`.
Eight focused source-selector/per-bit-view tests passed. No timing bench was
rerun for this packaging step, and all53 measured dependencies match main.
