# S81-COLL-STORAGEP1 review candidate

Opt-in RXSRAM=1 replaces the 553x8 landing FIFO with five 32x128 SRAM banks; default RXSRAM=0 and the legacy credit receiver source remain unchanged. The five banks allocate 20,480 physical bits for 4,424 logical bits, area 5,343.8616 um2. Continuous next-head reads plus current and previous logical-write forwarding preserve the visible receiver edges. Forwarding uses 1,106 unconditional payload register bits and 70 local select flags; no runtime-indexed flop array remains in this receiver.

Verilator 5.050 cycle equivalence: PASS 19,994 comparisons and 7,113 takes, W553 DEPTH8 WFREE1/2, overflow/drain/random traffic and mid-run reset. Disabling current forwarding fails 1,766 comparisons; disabling previous forwarding fails 1,862. WREG0 and WFREE0 are not qualified. Full xdie RXSRAM=1 positive and timeout/channel mutants are pending. Evidence: results/rtl/s81_coll_storagep1_1019.

Safe-design checklist before the sizing probe:
1. Pins: inherited registered landing/sender/gearbox boundaries; reset_landing two stages. Core-facing reset/clock sit beside register band. SRAM helper adds no external data edge.
2. Reach: explicit 561.6-square candidate; actual wire reach is a measured gate requirement. No parent-fit claim.
3. Fanout: SAFE per-consumer reset relay retained and expanded at the same depth. Each 16-bit forwarding slice has independent reset-distinct flags. Payload capture is unconditional. Actual synthesized fanout/depth must pass; no data masks.
4. Depth: existing endpoint send cone was about17 mapped levels, with prior positive setup margin. The new memory head is one SRAM read plus local forward muxes; exact setup/hold and SRAM timing remain unproved until measurement. No timing exception authorized.
5. Storage: all FIFOs/replay arrays over2kb use physical SRAM in RXSRAM=1. Five new 32x128 banks plus ten existing 512x128 banks, all physical area paid. Old flop-FIFO waiver is removed.
6. Geometry: explicit561.6x561.6 outline. Existing macro origins x43.2/259.2; new narrow column x475.2; all five rows at y43.2/129.6/302.4/388.8/475.2, on43.2 lattice. Minimum macro channel41.88um. Exactly one std-cell band y216..259.2; provisional area10495.7um2 is inherited only for sizing probe, must be replaced by actual synthesis and band resized to40-60% before CTS gate. Outer pins span full W/E face, <=2.7pins/um. Sparse fill uses reviewed lattice_channel_bound schema with measured geometry, never pin_bound. Final PNG review pending.
7. Clock: local spine, no >1mm root. TT and FF pin-flop spread must be<=80ps; hold margin0.03ns. No insertion-only waiver.
8. Schedule: static contract; cycle equivalence proves no added receiver data edges. Same-depth relay retains SAFE reset release: two landing + two sync + one relay, unchanged by SRAM. Native SRAM and full-link checks pending.

Regenerate using python3 physical/dscoll_cx/regen_safe_coll.py. Old gate outputs are evidence only. No REVIEW/submit until full checks, ROOT visual review, actual die-slot growth and physical pin escape proof.
