GF5 paired source profile (PRIVATE; default OFF)

Problem: routed gf4 fails TT-126.67ps on address decode -> SC forward mux -> SV face. Immutable failure evidence is results/gunit_core_1/gf4_routed_1113. ANALYTIC_MODEL.txt and IMPACT.txt record the pre-edit feasibility/7.11 approval, exact affected views and hazards.

OT_GUNIT_BF_SVREG adds a 512-data/22-metadata interior cut in F; existing SV/CTL face flops remain. Matching 256-bit bias snapshot stages in each A half preserve the original SRAM read value, including concurrent writes. No arithmetic/order/precision change. M1REG+C1REG remain enabled for this qualified private profile; all production recipes, pins, outlines and old signed views stay untouched.

The A SV/CTL-to-record interface latency does NOT gain another stage: F SV arrives one cycle later and A bias prefetch lead relative to it gains one. Whole-front select gains1; independent gather remains unchanged. Actual known-GU programme measures RT65/63 and RW103. Never double-charge A record latency or gather feedback.

Proof: bench/run_bench.sh OUT nominal|mut_ctl|mut_bias uses live repository RTL and the frozen full-band gf4 reference. Two seeds each:813 checks,168 selects,18 gathers,168 A checks,24 forwarding cycles,168 bias changes,12 concurrent read/write cycles. Nominal0 mismatches; metadata mutant455, missing-bias-delay mutant336. bench/check_default_off.py OUT verifies gf2/gf3/gf4 normalized preprocessing remains identical. Source snapshots/digests and small logs in proof/ preserve what ran; portable runner reads live RTL so a stale captured DUT cannot hide future edits.

Known calendar: existing gu_kit/run_gu_bench vehicle, GF5 define override,3 jobs/1655 HP-SC beats/15 CTL rows per side/50 roots/2rsqrt, no fault; wrong late/which calendars fail35/34. proof/summary.json includes exact observed IDs/weight timestamps and II1. Focused compiler row tests6/6. Default source recipes still gf4.

Private token price: ready12bA AR unchanged842.8004523tok/s; MTP2713.3087714 vs GF42713.3795791,48cycles/step (-0.00260958%). A IDs+1/RW+0 and conservativeB IDs+1/RW+1 give the same critical trace; analytic only, no adoption claim.

PHYSICAL HOLD: no P&R has run. The805ps stage1 feasibility estimate requires new data captures at the actual local forward-mux producer, not a midpoint on its230ps face wire. Constrain/render all512 data captures and22 paired metadata, keep face flops, then synth/LEC and private paired A/F builds. Review actual producer-to-capture reach before CTS/GRT. All three variants must re-sign before adoption.
