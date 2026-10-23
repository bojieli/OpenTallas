# Source-complete RTAG closure import

This packet imports record `8ed8a5a22` without its branch ancestry or helper changes. The source job is `s81bf_front_five_roots_n32_soq_roomy-ref-257fcb812`, source `257fcb812`.

The existing routed result is TT setup +0.00 ps, FF hold +16.92 ps, DRC 0, with child lint PASS. SS sensitivity is -300.13 ps; this is TT closure evidence, not SS clock qualification. The original verdict and view provenance remain unchanged.

All 45 physical RTL input blobs match the closed source. Of these, 39 already match the main base; six are imported here, including four existing canonical files and two new opt-in modules. SOQ and N32 default to zero in the canonical wrappers. The new kit explicitly selects SOQ=1, SOQ_SWD=160 and N32=1.

The exact kit, specification, 26 closure record files, positive and two causal-mutant logs and terminal receipts are retained. The positive compares 456 transactions with zero fault/busy. Read-copy and FP8-write-select mutants produce the required DIFF TXN failures. These are preserved observations, not new test executions. `observed_benches.json` copies current-source results directly from the CLOSED verdict; separately archived terminal JSONs retain their historical source5158641 identity and do not confer source credit on the current RTL.

The supporting BF transaction script carries the source's comma-separated define support and the two opt-in module inputs. Fixture trees, the mapped-ROM generator and ROM model match main byte-for-byte by Git object identity; `readset.json` records these checks. Python syntax and declared witness regexes were checked locally. No new simulation or place-and-route was run for this import.

No closure_loop, ref_tile, common_flow or tt_views helper file is changed. Die binding still needs the exact kit parameters, 1025 north-face pin projection, and clock-relay placement; importing this view does not itself qualify the die.
