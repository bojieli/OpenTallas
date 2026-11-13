# XS4 output face capture repair

Core r2 stopped before floorplan: 4904 checked boundary bits, 4824 good, 78 declared dead inputs, and two shared-output failures (xw_v and fault). Separate output flops had survived, but kept top aliases xw_vq and fault_q retained an otherwise dead BUFx2 load on each public output. The raw gate correctly refused those extra loads.

The output flops now live in dedicated kept-hierarchy one-bit capture modules, with the public port connected directly to the module output. The internal sticky fault state stays separate. No interface, outline, data, status, or reset latency changes.

Actual XS4 nominal production-program lockstep passes (XS4_EQUIV_BENCH PASS); the existing write-copy mutant is caught on L0 and L2 (20 mismatches on each programme). Logs: epyc7 hard-s81-dsdv-1/bench/xs4face3_eq.log and xs4face3_mut.log. An output-only mechanism synth fixture reproduces the old failures and clears both target outputs with the actual new helpers. The fixture auxiliary data0 reference output is excluded from this targeted probe; the real core boundary gate remains unchanged and will check every physical port.

The unchanged macro layout was rendered from the actual spec and LEFs and viewed in results/geom_review/xs4_core_r3_macro_review.png: 37 macros split north/south around a wide centre band; north-face data pins cover the width, clock/reset enter near the centre. PASS-COND for placement only. SMELLS to check in the placed DB: north-face pin density and access into bank columns; long north-face to south-bank reach; structured clock tap legality after CTS. The schematic deliberately does not invent clock tap sites. PDN continuity remains a physical-flow check.

Fresh core r3 kit hash fe3a98089492da02 was generated with the two new helper modules in synth_keep_modules. Full raw/mapped face guard and physical closure are pending. Old r2 FAIL is retained.
