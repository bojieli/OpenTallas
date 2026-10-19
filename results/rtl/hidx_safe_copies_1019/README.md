# HIDX inherited control distribution experiment

SAFE_COPIES is default-off and composes with SAFE_RING=1/SAFE_CARRY=1. The production interface,20-bit record IDs, mutable SRAM r2c2 contract, exact record order, and historical+5edges remain unchanged. No route, die binding, native timing, or single/multi-user token qualification is claimed.

First6d56dbaa4 source passes actual5.050 production3072records/1282miter, all fills, maxpack71, error0, fixed+5 output/fault. Full mapped census is live, with exact source retained in its immutable remote src.

Extended5af00a1ab passes the same3072records/1282miter/error0, with first_tx187->192 and fault1282->1287. Causal mutants7/8 fail180/162 checks. SHA25635633c53 pins the exact tested source. Actual final mapped census1450365/session98861 is live; no fanout success is claimed.

The extended source distributes pin-age lane masks, per12-bit merge/rotate/write controls, per6-bit cyclic carry mux controls and per12-bit emission enables. Mask rotation has separate selectors. Real retained inversion-pair trees bound source-D and reset branching without adding a register edge. This is not a physical timing repair by itself: the actual combined combinational depth and all mapped drivers must be measured before any physical build. MODEL.md records FF/logic/area reserves before the extended build.

Original two-stage face reset landing remains. Local reset branches preserve its assertion and deassertion value, without masking faults or introducing extra release edges. The actual maximum mapped fanout and source-preserved local copies are pending census.

Causal mutants7/8 respectively corrupt one local rotate control and one local SRAM read-bank selector. Their production-shape failures are required alongside the extended positive, before any gate. Existing six-mutant and ring proofs remain in the base branch; the new source is not promoted using those older positives.

Eight legacy64x512_r2c2 SRAM faces are dense and off lattice. Central macro access/repair assumptions, legal physical rows/PG, matched SRAM/native clock branches, reach<=405um, full faces and root PNG/checklist review remain separate blockers. No geometry change, critical REVIEW.json or submit was made.
