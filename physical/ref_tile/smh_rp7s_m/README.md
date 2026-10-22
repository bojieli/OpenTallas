# SMH r7 south MAIN

Actual native census PASS: max32, zero violations, zero role errors. Production-width retiming miter:5,486 comparisons/0 mismatches PASS; causal bypass mutant:2,743 mismatches, expected FAIL. Source ring compensation, all qualified children and outline unchanged. No layout/timing/first-token-frame qualification yet.

1_pins: Existing registered faces kept; face stages now use their own landed root. Original hard-child pin registers unchanged.

2_reach: Face/body and x-store/body paths all enter fixed-latency D4/E2 rings; regional placement boxes retained. Actual placed reach remains a gate obligation.

3_fanout: Kept W24 landing reset field copies and same-edge per-consumer reset copies. Native census must pass before layout; no waiver.

4_depth: No arithmetic logic added; all schedule compensation is registered. Original hard children unchanged.

5_storage: Landings are D4 rings. Additional delay compensation is a fixed-throughput chain of three-slot rings in kept eight-bit chunks; no indexed wide flop store or long shift pipeline. Same 3/6/9/12 data-edge ages; phase reset copies are bounded.

6_floorplan: Unchanged 691.2x1252.8 pin-bound outline; original hard children and 43.2 lattice retained. Face groups never shrink the qualified macros.

7_clock: 9 landed regional roots; face pins separated from hard-child insertion, x-store on own root; child centring taps; TT/FF within-region spread <=80 remains required. Hold margins 0.03.

8_schedule: Static retiming against r6, interface output offsets {'rout_s': 6, 'gout': 12}; regional reset depth 4. Edge equality recorded for every source/read pair; exact miter and priced composition required.
