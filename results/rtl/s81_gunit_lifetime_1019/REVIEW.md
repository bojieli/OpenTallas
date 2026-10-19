# Scoped source proof; physical adoption blocked

This packet characterizes the actual FANOUT_SAFE table branch from gate2 d9ef2759827ab649e467ad5cb7e171f3e97c696f and provides a default-off TABLE_LIFETIME_SAFE correction. The vehicle extracts the source branch byte-for-byte and instantiates the unchanged native macro. Inputs are the actual registered table boundary (`wv/wa/wd/tj_set/tj_w/ln_c`), not package pins. Arithmetic, scales correctness, production configuration fencing, and external launch timing are outside this minimal base-table proof.

Original three-seed Verilator5.050 runs each compare all96 explicitly programmed nonzero words across four logical rows, perform eight consecutive qualified captures, sweep write→launch distances0..6, exercise selector-switch/write coincidence and reset abort/recovery. Original logs retain both causal misses: same-edge selected write at launch with old hit0, and a write to a future selected row before its selector pipeline catches up. Original window1..4 does assert;5..6 clear. No macro/FF memory was initialized to artificial zeros (`OT_MEM_NO_INIT`, randomized reset seeds1/17/241).

The native macro has blocking writes and a separate read process on coincident clocks. This proof does not call collision data OLD or depend on event scheduling. The correction rejects selected collisions, while noncolliding, fully programmed captures compare exact nonzero words. A cold launch before programming returns no hardware-valid fault: this is an explicit OPEN source contract, not a qualified positive. No assumed software fence supplies this missing proof. Warm reset data retention does not establish cold configuration admission.

Checklist scope:

1. Pin registration: inherited exact table boundary; no change, full package proof OPEN.
2. Reach: +9 local history FF modeled; physical reach OPEN.
3. Fanout: proposed per-row histories and one selected comparator; full mapped/native all-driver census OPEN. No SAFE qualification claimed from source arithmetic counts.
4. Depth: 3-bit decrement and4-way timer select plus same-edge row compare; placement RC/TT+FF electrical depth OPEN.
5. Storage: twelve native32x64 banks unchanged; only12bits of counters. Payload3072bit storage remains SRAM.
6. Floorplan: measured W/E103contacts each/17.304um=5.95238/um; aggregate density PASS. Old206/32 arithmetic WITHDRAWN. Contacts occupy0.780..10.572um at0.096pitch; full-face redistribution and twelve-bank local escape OPEN, no coupon waiver.
7. Clock/reset: no new domain/edge; resetregion3 source load11→20 modeled (includes+9); all global/reset cone native counts OPEN.
8. Schedule: zero added cycles; HC1015N/1013S unchanged by construction, actual composed replay not repeated here.

No gate, route, REVIEW.json, main import, macro waiver, full arithmetic pass, or token qualification is authorized by this packet.

Correction outcome: TABLE_LIFETIME_SAFE=1 passes1412 edge/check observations per seed1/17/241, including28 row/distance windows, all16 old/new selector transitions,12 nonselected simultaneous write/launch cases, and warm-reset payload retention. Two causal guard mutants fail as intended: removing same-edge detection fails WINDOW_FAIL gap0; rekeying row-history arming to current delayed selector fails SELECTOR_HISTORY_FAIL. Unmodified original guard failures remain in original_seed_1.log and collected/seed_{1,17,241}.log. No payload zero assumption is introduced. The old diagnostic text `physical_contact_density=206/32=6.4375` in immutable run logs is explicitly withdrawn by measured macro_face_contacts.json above.

Next: prove actual production configuration-valid/launch fencing for cold and every relevant reset; perform full source/native uncapped reset/fanout checks with TABLE_LIFETIME_SAFE=1; close actual twelve-bank full-face escape and parent slot before any gate. Existing live gate2 remains its original source, without this opt-in correction, and cannot inherit these source results.
