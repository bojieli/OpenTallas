# GUNIT whole-source successor model — ROOT decision required

Source `12ab196b6`; immutable mapped evidence `3ca0d8055`. This is a complete
analytical census and a proposed structural construction, not source, timing,
geometry, or build admission. No RTL, synthesis, placement, CTS, or route retry
was performed. All 19 original source hashes remain matched; archived git identity
remains null rather than being inferred from the branch.

## Every finding is accounted for

`whole_model.json` contains every affected native root, original and expanded
consumer pin counts, consumer families, required useful replicas, exact TT master
area, complete 19,771-FF storage census, and library hashes. The 1,874 original
offenders reconcile exactly: 410 flattened Boolean, 1,437 Sinkhorn-labelled,
10 multiplier, 16 other, and one reset. The old first-1,000/truncated console
lists are not inputs to this model.

The construction duplicates actual useful Boolean producers or same-edge state
equations, partitions their real consumer pins into groups of at most 24, and
recursively charges every replicated D, enable, and reset pin upstream. BUF/INV
trees are transparent. The 24-pin target leaves eight pins of margin under the
32-pin admission limit; it is not a new threshold or a timing waiver. Original
masters and every original consumer remain. Duplicate FF clock, reset polarity,
assertion, D equation, and enable equation must match exactly. Native cells must
be kept against merging; replacing this with buffers would invalidate the model.

The fixed point converges after three demand updates and a fourth unchanged
round. It adds **4,536 useful cells, including 3,133 FF**, and
**1,054.01736 µm²** of actual TT master area. Existing mapped area is
33,064.74270 µm². A conservative allowance of two INVx1 per added useful producer
costs 396.80928 µm²; these preserve polarity and provide no logical load relief.
Thus the useful-copy construction reserves **34,515.56934 µm²** before SRAM and
fault changes. Added FF clock capacitance is **1,486.460113 fF** in the pinned
TT Liberty units. Dynamic clock power rises; no energy or rate gain is claimed.

The largest family additions are 1,592 predecode FF, 360 seed FF, 295 denominator
FF, 260 X-mantissa FF, 185 quotient FF, 108 table-select FF, 83 step-zero quotient
FF, 54 launch enable FF, 47 multiplier FF, 40 mode FF, and 36 row-add/normalizer FF.
The complete JSON includes all smaller control, state, reset, and Boolean families.
Copies already introduced by CONTROL_SAFE are retained; this is an incremental
price against the actual current map, not a second charge against safe3.

This fixed point establishes a feasible *logical pin partition*, not spatial
locality, placement survival, source correspondence, or mapped timing. Added
combinational loads can change slew and delay. Per-root exact useful-consumer
assignment and native correspondence are mandatory implementation outputs.

## Runtime storage and the actual base-table ports

The full FF inventory includes **base_t[96][32] = 3,072 mutable table bits**.
This exceeds the 2 kb SRAM rule. Other large state in this block consists of
separate 768-bit operand/state words, 512-bit Sinkhorn matrices, fixed pipeline
registers, and 384-bit scale storage; immutable reciprocal coefficient decode is
ROM logic. It would be incorrect to call the existing base table SAFE because
the fanout repair itself adds no arrays.

Concrete candidate: 12 parallel exact `ot_sram_1r1w2c_32x64_m1` banks from
`e26d92503`, representing four logical 768-bit words `{set,which}` in physical
rows 0..3, with 28 unused rows per bank. Capacity is **24,576 physical bits for
3,072 useful bits**, raw macro area **6,643.074816 µm²**. Both actual clock ports
are paid: 12 × (9.3458 + 9.3458) = **224.2992 fF**, even if tied to one root.
The primitive's independent route coupon is not a 12-bank qualification.

Each 256-bit config write updates four 64-bit banks. Config row offsets 0..2
select bank groups 0..3, 4..7, 8..11 in `which=0`; offsets 3..5 select the same
groups in `which=1`; the other address bit is `wa[8]`. All 12 banks read one
768-bit word in parallel. Upper physical address bits are tied to zero; write
masks are all 64 bits for the four selected banks. Read address demand is 12
macro pins per active address bit, before local keep/control proof.

Original table select has two kept ranks: `tj_* -> g_tj1 -> g_tj2`, followed by
the registered `bases` capture. A synchronous read from the existing second-rank
select can replace that last `bases` capture without adding a qualified launch
edge: select at edge a, rank1 a+1, rank2 a+2, native read/output a+3. Bank-group
selects must be shown to represent the same two-bit owner; arbitrary byte ranks
cannot be silently combined during transition.

**Admission blocker:** same-address dual-clock write/read ordering cannot be
assumed. The source currently permits config writes while continuously reading.
An actual production lifetime contract must prove selected table words are not
written during the qualified read/launch interval, and that config has settled
before the first qualified read (or a real old-read cache must be modeled).
The existing >=29-edge job-select lead time is potential slack, not that proof.
Until compiler/producer ownership and collision/reset/abort tests prove this,
SRAM replacement is not implementable as an exact drop-in. No same-edge table
read or hidden initialization assumption is licensed by this model.

## Fault stage: explicit extra edge rather than unchanged-age assertion

Current diagnostic depth is 661.8 ps / 17 levels, `tc_q[21] -> flt.D`.
Useful copies alone do not resolve it. Candidate Q4 registers six exact bits per
quotient: `inc1`, `inc2`, `high0`, `high1`, `low`, and `zero`. Here
`high0 = !sub && signed11(E+127)>254`,
`high1 = !sub && signed11(E+128)>254`,
`low = !subn && signed11(E+127)<1`.
The signed 11-bit wrap is retained; replacing these with an unbounded E threshold
would be wrong outside the valid numerical range.

After Q4, use the unchanged stable `ms_q` to compute carry and original pack:
`ovm = inc2 ? &ms_q[23:1] : (inc1 && &ms_q[23:0])`;
`range = !zero && ((ovm ? high1 : high0) || low)`.
The old `ms_q`, `s_q`, and `E_q` remain valid until the next step's Q2; no hidden
extra operand bank is needed if the recurrence is delayed as proposed. Exact
reset/abort/restart and early-valid behavior must prove that lifetime in RTL.

This needs **96 logical unreset FF**. Reserve two useful copies of each predicate
(**192 physical FF**) to partition correction/packing consumers; FF area is
55.9872 µm² plus16.79616 µm² conservative polarity allowance, with
**91.149312 fF** clock input cost. Incremental predicate Boolean logic is also
paid: per quotient, two11-bit adders at5 two-input gates/bit, three11-bit
constant comparisons at3 gates/bit, plus8 mode/zero gates =217 gates. For16
quotients reserve **3,472 gates at0.2916 µm² each =1,012.4352 µm²**. This explicit
small-gate construction is conservative and takes no credit for existing
comparison gates it replaces. Its E-bit loads add two adder inputs to each
original copied operand group (24→26 at worst, still<=32); intermediate ripple/
compare signals have small local fanout. Actual source mapping must replace
these analytical charges and inspect every new packing/control consumer.
The original inc/pack arithmetic is retained with a new boundary, not numerically
reordered. The independent integer model checks **458,752 cases**, including all
signed 11-bit exponents, both subnormal/zero modes, both correction controls,
and mantissa carry boundaries. That verifies the algebra only, not RTL ages.

Explicit calendar price: **D0 17→18, DS 15→16, LAT 602→642** for ITERS=20.
One step-zero and 39 steady steps add **40 edges per HC job**. HOP ages become
candidate **1015 N / 1013 S** from the same lastHP_N origin, versus 975/973.
At the selected gate period 0.77 ns this is 30.8 ns/job; at 1.2 GHz model pricing
it is 33.333 ns/job. A two-HC serialized layer pays 80 edges / 66.667 ns at
1.2 GHz, before actual overlap/critical-path composition. Compiler reservations,
CTL outputs, END, and token pricing must change together. Existing golden8,
decoder2048, and HOP975/973 evidence remains narrow evidence for old source;
new source needs golden/HOP and old/+1-age mutant witnesses again.

The proposed boundary removes final packing and global fault reduction from the
remainder-sign stage, but no unmeasured <=600 ps claim is made. New mapped depth
must check both Q3→Q4 and Q4→state/fault; any other deep path remains blocking.

## Reset, clock, area, geometry, and model decision

The model's old reset143 expands to202 logical reset-pin loads, requiring nine
same-edge copies of that final reset output (+8 FF, included above). Direct raw
asynchronous reset contacts would grow from six to14 if the old relay were copied
unchanged. This is disclosed, not SAFE. Candidate ownership: keep the two original
raw-asserted synchronizer FF; asynchronously clear final region FF from sync_q[0],
while their D still reads sync_q[1]. Raw reset then drives two FF, sync_q[0] drives
one D plus12 final async clears, and final region release remains edge3. Assertion
now traverses a real FF asynchronous-clear→Q path; minimum pulse, native recovery,
assertion propagation, simultaneous reset/clock, and parent first-valid guards
must be priced/proved. This is a source/reset contract choice requiring ROOT
review, not a claim that the old direct assertion is electrically identical.

Conservative combined reservation is **42,243.862716 µm²** including raw SRAM,
while taking *no* area or clock credit for deleting the old 3,072 table FF or
768 bases FF. Worst provisional clock census is **23,096 FF +24 macro clock pins**;
copy plus predicate plus macro clock cap increment is **1,801.908625 fF** before
credit/CTS buffers. Measured post-conversion mapping must replace this bound.
Do not reuse the old 280.8-square or259.2-square slot approval.

A diagnostic candidate is 388.8×432 µm, one full-width standard-cell band
y129.6..302.4, 172.8 µm high. Its 67,184.64 µm² band reserves 52.99% for the
35,600.7879 µm² conservative standard-cell mass. Twelve real macros can use
x43.2/172.8/302.4 and y43.2/86.4/345.6/388.8: all origins on43.2, horizontal
gaps97.608 and vertical gaps25.896 µm, outside the band. Macro origins are a model,
not actual placement. This tile is 2.5× the old259.2-square area. Actual parent
fit, source-region grouping, clock beside register mass, all <=405 µm pin paths,
full-face <=6 pins/µm, actual PG/via escape, and paid post-hold cell mass are OPEN.

ROOT review requested: choose/modify the paid Q4 age, SRAM lifetime contract,
reset assertion ownership, and enlarged parent reservation before authorizing a
bounded source prototype. Full RTL build and physical gate remain blocked.
