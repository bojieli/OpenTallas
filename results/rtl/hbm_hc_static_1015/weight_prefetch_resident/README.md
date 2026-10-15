Four-row resident native HC weight component
============================================

The original434-SRAM six-position composition missed row2 half1 at edge8880. Exact320-SRAM phase replay measured readiness at9012,132cycles late; the historical failure remains committed. Reserving12cycles sooner was insufficient.

New versioned source29272fdde partitions the existing128 staging macros into eight512-sector regions per stack, retaining four HC rows. The compiler primes four rows at an explicit cold boundary, then reserves row+4 at fixed ages330/660 and drains at0/330. Periods remain1080/1400; every actual HC SRAM row commits by age655. Opposite halves occupy distinct physical macros. Epoch low2bits select storage; full16-bit epoch,3-bit region,11-bit ordinal and unique17-bit tag guard ownership. No peer controller source changed.

Nine positive cases use actual a7 owned digital controllers, canonical command-only23-edge DRAM fixture, released checkpoint bytes,128source+128controller+64HC SRAMs. All24rows and61440real HC memory readbacks pass per case. Critical case reproduces full-join sample edges7470/8550/8880. Cold four-row initialization measured1245..2486stream cycles across the exercised phases; startup cost is explicit. These samples are not an exhaustive latency bound.

Same-region stale epoch+4, corrupted response tag, and actual offchip payload mutants are rejected. Baseline8positives passed before a testbench fallthrough caused expected owner rejection to print PASS and then fatal. That failure and original cache are retained. cad2e3b94 adds exactly one else in the bench; normalized sources prove positive paths and every DUT source unchanged. Follow-up critical positive and all3mutants pass with source hashes verified and no UNOPTFLAT/LATCH/MULTIDRIVEN warnings.

Canonical G25 P1 stride0 remains unqualified: four AP lanes need640cycles versus its approximately355cycle budget. Full SYS1 nativeVM/arithmetic/programme composition, physical clock/slot/pin/timing closure, full2064row hardware installation and ACK remain separate open work.
