# Bounded CSA source model before native proof

Immutable predecessor c34a0e781 and model c07103474 retain their failures.
This successor changes only the opt-in standalone count helper; production
RTL 5af00a1ab, compiler schedules, helpers and physical gates are untouched.
The original compaction helper is byte-identical. Both count trees per cohort
are complete useful arithmetic; each has twelve existing selector FF D loads.

Exact static inventory: 12 pc8 trees at 4 FA + 3 HA and 24 pc16 trees at
11 FA + 4 HA = 312 FA + 132 HA (444 retained arithmetic leaves). FA has
sum=a^b^c and carry=(a&b)|(a&c)|(b&c), HA has XOR/AND, with unique elaboration
IDs and inherited keep_hierarchy. No combinational buffers or added FF.
Each first-stage operand enters three FA input functions per tree: at most
six useful native gate contacts before map, plus any actual polarity repair.
Final count owns exactly twelve real FF D; mapped count/cap/slew must confirm.
Whole-input ownership: first byte has 9 compaction+6 pair+12 quad=27 mask D;
second byte 12 quad mask D; payload bits one FF D. Canonical/S1 consumer is
outside this coupon: whole source maxima 28 (group pattern 28/22/16/10).
Native whole-source ownership remains required before source adoption.

Existing coupon FF: 72 compaction-mask + 288 payload + 48 pair-mask + 192
quad-mask + 576 pair-selector + 1440 quad-selector = 2616. Reset endpoints
remain zero in this bounded helper; whole-source reset landing is NOT solved.
Clock contacts and logical ages unchanged: inputs captured at edge 1, count
selectors edge 2. Internal gc compaction remains combinational to its existing
external S1 FF; there is no hardened registered-output claim.

Primitive reference cost from c07103474 is 247.21848 um2 / 2448 cells for
count arithmetic, replacing old count logic, not adding to it. Conservative
coupon budget 1333.47222 um2 is not a measured fit. Existing clock cap
1241.909376 fF and FF cost should remain equal; final native values required.
MAC and memory traffic zero for this integer count/compaction coupon; no new
storage, rings, request slots, crossing bits, token edges or sustained-rate
claim. Payload width 288, count selector width 2016 remain unchanged; entire
HIDX/SRAM density/reset/boundary model stays HOLD.

Before mapped proof: source all 65536 masks, all 256 compaction masks times
288 payload basis+zero, random arbitrary payload; independent symbolic
append/count source SAT and native mapped SAT; five inherited mutants plus
wrong CSA carry (six). Native all-driver BUF/INV-transparent census must
include input, FF Q/QN, combinational roots, all real D and output sinks,
constants and unknowns. Genuine hierarchy retention inspected from native
hierarchical JSON; no name exemption. Original 833ps / setup60 / hold25.
Admission requires <=32 nonclock loads, body <=600ps, margin >=30ps, all native
slews <=320ps and caps within exact Liberty. No routed FF hold or SS claim.
A miss requires another structural MODEL, no unchanged route retry.
