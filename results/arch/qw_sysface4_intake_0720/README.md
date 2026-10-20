# SYSFACE n32o / n32oa critical intake, 2026-10-20 07:20 takeover

**HOLD: neither tile is approved for submission or parent binding.** This packet preserves the exact completed gates and independent read-only native audits. It does not change canonical RTL, kits, macro views, or shared flow helpers.

Source owner: `claude/qw-sysface4-1020@48d157145fd6ea9c34be8b90a6e6d4abeb2618f0`. Both gates captured exact content snapshots; their gate_result.json contains the complete source manifest and helper overlays. Selected hardware and source-proof files are preserved in `source_snapshot/`; kit/gate/image files in `snapshot/`. SHA manifests accompany both.

| Result | n32o, original ROM | n32oa, escape apron ROM |
|---|---:|---:|
| Completed gate | WARN, 0 fail / 1 depth warning | WARN, 0 fail / 1 depth warning |
| Trial-route overflow | 0 | 0 |
| Complete clock spread TT / FF | 51.7 / 53.3 ps | 50.2 / 52.4 ps |
| Boundary clock spread TT / FF | 41.4 / 41.1 ps | 39.8 / 40.4 ps |
| Macro lateness flag | false | false |
| Mapped depth | 834 ps, 28 levels | 834 ps, 28 levels |
| Placement-RC diagnostic setup | -63.2 ps | -55.9 ps |
| Actual GRT dynamic terminal fanout | max32, zero >32 | max32, zero >32 |
| Actual GRT transformed pin-bbox L1 reach | max319.707 µm, zero >405 | max319.605 µm, zero >405 |
| Native PG terminals / unbound | 137738 / **11028** | 137626 / **10692** |
| Other missing functional ITerms | 0 | 0 |

The missing-output lists contain 478/491 native dummy clock-buffer outputs. Classification uses exact instance correspondence to a Liberty-proven unary buffer whose input belongs to an actual clock:true/native CLOCK seeded network. It does not use instance-name prefixes. Raw missing lists and PG failures remain in the compressed reports.

The PG failures include actual `rebuffer*/VDD,VSS` ITerms inserted by the flow. They are a real blocker. No original ODB was changed; before/after hashes are byte-identical. A rerun must establish PG binding at cell birth before protection/timing analysis using an admitted flow; a late cosmetic connection or changing audit exclusions does not qualify this gate.

The original ROM uses 96 nm contacts at about 10.4 contacts/µm and retains its contact-rule failure. The escape-apron ROM uses 192 nm pitch at about 5.2 contacts/µm; its Liberty remains explicitly **PROPOSAL-ONLY**, with no physical-memory qualification implied by this gate. Its new outline/contact/source contract still requires ROOT review.

The 07:11 coordinator decision accepts the approximately 3.5 kb of SYSFACE calendar flops as static configuration storage: tables up to roughly 4 kb may remain in flops when written only during config/boot and read through a registered mux. Dynamic storage remains subject to the SRAM requirement. This accepted exception must be copied into a future runnable kit README; the immutable original kit snapshots remain unchanged here.

Existing source proofs cover the actual MU1/MU_HEAD1 protocol for 250777 cycles from the first epoch, constant configuration outputs, the unread original `seq_dc[54]`, and the new registered `obs_fault` path with its causal mutant. `obs_fault` adds two edges to the fault-observation path; g5f still needs real post-relay fault collection and a qualified physical sink. The 834 ps stage warning and negative diagnostic setup remain visible; no cycle or timing mask was introduced in this intake.

All four floorplan/density PNGs were personally inspected. The floorplans retain the same 259.2×129.6µm outline, north clock entry and one ROM at the literal 43.2µm lattice origin (172.8,43.2). The apron expands the ROM toward the east; surrounding rows remain visible and no macro overlap is shown. Density is concentrated along the upper pin band; images alone are not a pin, PG or timing proof. Image-caption fills are 30.5% / 32.3%; source/pin-bound sizing review remains part of the critical packet.

Read-only jobs ran unpinned through ot-run, 8 GB / 1 thread, on the host with the preserved run directories. Both completed exit0. Full per-driver rows remain at `ot-epyc9:/srv/opentallas-scratch/claude/codex-qw-sysface4-audit-1020/{n32o,n32oa}/rows.json`; their SHA256 identities are in each concise receipt. The code and commands used are preserved in this packet. Native audit scope covers actual standard-cell Liberty roles, native macro terminal direction/clock roles, terminal connectivity, transformed geometry and bound PG ITerms; it is not a conductor/via/short proof or a physical-memory characterization.
