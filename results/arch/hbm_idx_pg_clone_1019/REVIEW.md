# IDX256 isolated PG binding diagnostic: ROOT review requested

**Diagnostic PASS; released artifact remains PG_HOLD.** This packet changes only a separate clone of exact `hdie_col_idx256_1019-fan32g1-2727e1f68`. No reroute, gate, submission, source helper activation or parent adoption occurred. ROOT alone may choose any next action.

Original routed ODB SHA256: `851903b3ea016e159ac50862a1c80c5b3f4c6276e13df27789182736ce4e72c6`.
Clone ODB SHA256: `22e4a3d00d57b5d0b9c69e92bd26b4ca351b95b179f3fce416c065a34e79821a`.
Original SPEF SHA256: `a86653e98ff953e441f905ec66347cec4a7dd5cfb453b33f3903b59a8e2c29a2`.
Original input is mounted read-only and its ODB/SPEF hashes remain unchanged. Clone ODB lives at `ot-epyc7:/srv/opentallas-scratch/claude/hbm-idx-pg-clone-1019/clone.odb`; the original daemon route path is recorded in the preceding final-native packet. Full before/after raw native graphs, DEF serializations, physical conductor export, allowlist, invariants and full strict census are committed here as compressed artifacts; clone binary stays on the fleet with its hash.

## Exact modification and invariants

`clone_summary.json` enumerates all 644 original missing PG pins on exactly 322 `BUFx24_ASAP7_75t_R` clock instances. Only those pins are connected to the existing VDD/VSS nets with matching POWER/GROUND roles. Native dont_touch prevents direct modification (the first diagnostic attempt aborted with ODB-0369); the successful isolated clone temporarily clears protection on each exact instance, binds its PG pin and restores the original protection without invoking any physical engine. All original instance names, masters, positions, orientations, placement status, protection flags, signal-pin connections, BTerms and native routed-wire inventories are unchanged.

The complete native DEF serialization outside NETS/SPECIALNETS is byte-identical. Every signal NET record is byte-identical. Every PG wire/via geometry token is unchanged. Native direct connects appear as additional VDD/VSS terminal records in NETS as well as SPECIALNETS; these are PG metadata records, not new signal routes. DEF net-count serialization changes accordingly, while the actual native net inventory remains 30,282 before and after. `def_invariants.py` asserts the complete comparison. No new cell, route, via, outline, placement, area or schedule edge is introduced; zero geometric cost is established for this exact existing rail-contact case only.

## Complete conductor/contact graph

`metal.json.gz` contains 1,973,260 actual native master-pin, BPin, supply-wire and native via shapes. The graph never joins shapes merely because they share a net name. Same-layer conductive shapes connect only on physical contact; each actual via cut must be fully enclosed by both native adjacent metal landing boxes before it joins layers. All 33,945 via instances and 1,696,320 individual cuts pass. All shapes lie on the native one-DBU manufacturing grid.

All 196,864 native PG terminals, including every shape of each formerly unbound pin, connect geometrically to their matching VDD/VSS BPin supply network. Each supply forms one component. There are zero VDD/VSS same-layer contacts, zero wrong-supply reachable terminals, zero uncovered native PG pin shapes and zero via enclosure failures. The old exact row/rail overlap receipts remain in `535afd687:results/arch/hbm_idx_final_native_1019`; unchanged cell/geometry assertions preserve those legal-row facts.

This proves native OpenDB/LEF conductor contact/connectivity and absence of VDD/VSS geometric shorts in that representation. It does not claim transistor/GDS ERC, extracted supply resistance, IR-drop or commercial reliability qualification.

## Complete strict native census after cloning

Fresh export includes all 98,432 physical instances, all 76 native masters and their complete native pin inventories, all 2,332 BTerms and all 30,282 nets. Actual POWER/GROUND roles are independently validated before the logical diagnostic removes PG pins/PG-only physical cells. Native real Liberty functions establish BUF/INV transparency; no clock-name or instance-name exclusions are added.

Strict logical result: PASS; 30,237 cells, 30,535 roots, 57,401 endpoints, 5,417 FF roots, 24,674 combinational roots, 298 top-input roots and 146 physical tie roots. Maximum nonclock transparent fanout 32; zero violations, unknown virtual literals or canonical/transparent violations. The 255 original open-output clock-loading buffers retain their real input capacitance receipts; no zero-capacitance claim follows from an open output. `clone_strict_census.json.gz` and full compressed summary retain all details. The original source-to-netlist equivalence limitations of this diagnostic are unchanged.

## Frozen helper source order and proposed correction

See `SOURCE_MODEL.md` and immutable `source_order/`. Exact CTS creates 322 clock buffers; `clk_net_protect.tcl::ot_protect_clock_tree` then protects them before repair_timing_helper. Final `final_report.tcl` calls `final_connect.tcl::global_connect`; all 322 protected instances are explicitly skipped with ODB-0383. Subsequent net-only PSM reports supply shapes connected because those unbound terminals are absent from its net membership. Native stage counts and original warnings are preserved.

The bounded source proposal binds and verifies each native PG terminal immediately BEFORE its instance becomes protected, using its actual declared voltage-domain supply mapping, then retains existing clock protection. Final all-native-terminal coverage runs after final global_connect, independently of PSM. Intermediate stage counts remain diagnostics under the existing flow contract. Unknown/ambiguous domains refuse. ROOT-merger must separately implement and test default/coherent flows plus a causal protected-buffer negative before any shared helper activation. No shared helper is edited by this packet.

## ROOT PNG and checklist pickup

`original_gate_floorplan.png`, `original_gate_density.png` and `original_ROOT_FINAL_REVIEW.md` are byte-identical copies from `795d679b2`; that document records ROOT's original personal geometry review and the narrow low-fill exception. Original source/kit geometry fingerprint is `b44057faf45222632b3bb2eb75a32eb13868819d5b17a28754ceae394f891c4d`. These historical CTS images are not newly rendered final-route PNGs. Final clone placement is exactly unchanged from the original routed final ODB by full DEF/instance comparison.

Checklist scope: registered signal pins and unchanged two-sampled-edge reset PASS; conservative 259.2 um outline Manhattan bound <405 PASS; complete actual fanout <=32 PASS; original bounded combinational stage depth retained; no SRAM required for guarded 256-row shape; 129.6 um square, no macros, continuous legal rows and frozen full-face pins PASS, original pin-bound low-fill exception retained; routed own-clock spreads TT46.3/FF41.2 ps PASS, neighbor/parent matching remains OPEN; exact original static calendar and functional benches retained with zero added edges. Original routed TT setup +92.98 ps / FF hold +19.39 ps, DRC0, antenna0 and electrical-zero-violation receipts are unchanged historical timing evidence; timing was not re-extracted on this metadata-only clone.

Parent ANY prm assignment, NF5 exact die binding, neighbor native budget and composed production throughput remain open. Full SU/MU token qualification is not established.

## Execution receipts

All OpenDB exports, conductor proof and native census ran through unpinned ot-run with actual data locality on ep7. Successful units: `oth-ubuntu-42214-1792441051` clone/export; `oth-ubuntu-45261-1792441183` initial contact and clone raw export; `oth-ubuntu-46703-1792441268` full-enclosure proof (then shell copy stopped on root-owned output permission); `oth-ubuntu-47394-1792441326` strict native replay plus complete DEF invariants/compression, exit 0. The permission issue was resolved only on this lane's created artifacts. The first direct-bind diagnostic aborted as expected on native dont_touch; source/order/RAW failure records remain immutable. No fleet job remains live for this packet.
