# Review-only HIDX count-D structure after coupon1

This extends immutable failure c34a0e781. There is **no new RTL, mapping,
simulation, pipeline, physical job or adoption**. Seven/fourteen cohort tuning
is not selected. Original full source remains5af00a1ab and storage/reset holds
remain independent. All costs below are a source model, not measured new gates.

## Failure that the structure must repair

The actual quad-count bit3 path has652.509ps combinational delay, consisting of
272.903ps low-fanout body and379.606ps in its last two useful count gates. The
latter drive25contacts/13.947189fF and24realFF D/13.411732fF respectively. The
actual FF launch54.819ps makes707.328ps total. Eight serial XOR/XNOR cells in
the body show that a balanced arithmetic expression alone did not preserve a
balanced native cone. Maximum slew is474.66ps on pair-count bit3, limit320ps.
Fanout27/no literal violations does not qualify electrical or depth behavior.

A valid successor therefore needs BOTH useful arithmetic boundaries that stop
that long reshaping and actual lower per-result electrical load. All bits,
operand Qs, D sinks and transparent paths must be recounted after canonical
mapping. Physical repair or a hierarchy attribute by itself is not proof.

## Candidate ownership at the same age

Keep the original six pc8 and twelve pc16 **registered operand cohorts** in this
coupon. Each current24-selector cohort owns two complete useful arithmetic
networks, each driving12 of those existing selector FF. Both networks consume
that cohort's actual mask FF Q, at the original edge; there are no buffer trees,
new pin-copy FF or new clock edges. Each network computes a genuine count.
It is not a split output alias of one arithmetic root. Do not share/merge the
actual useful count outputs between the two networks.

This preserves original FF cost and input ownership: coupon mask input first
byte9compaction+6pair+12quad=27, second byte12. The whole model includes the
existing canonical/S1-count consumer: group counts28/22/16/10 repeated, max28,
1216 valid pin operands total. No raw input-count consumer is silently omitted.
The selector count remains144*4+288*5=2016 FF in this coupon and2304+2880 FF
across all four pairs/two quads. Added mask/selector FF, reset endpoints, clock
contacts and logical token edges are all **zero in this source model**; final
native retention, timing and full compiler/clock model must confirm them.

Every first-stage FA operand appears at most once in the XOR sum plus twice
in the three majority ANDs, i.e. three real gate input pins per network. Its
shared mask FF Q therefore serves at most six useful first-stage native-input
roles for two networks, before actual mapping; ordinary outputs of those mask
FF have no compaction/canonical consumers. A raw mask input still serves27
actual pin FF D, and the independently owned compaction masks retain their
previous measured native maximum14. This must not be implemented by reusing
one of those compaction mask Qs without recounting its other logic.

Arithmetic sum/carry nodes move to exactly one later compressor/adder; at most
three useful input contacts per later FA, two per HA. Final count sum bits own
12 FF D (reference6.705866fF, half actual24-sink load); final carry is a distinct
arithmetic output, not the same output distributed to another count bit. Those
are source role bounds, not a prediction that canonical ABC will satisfy them.

## Two genuine arithmetic alternatives

Both alternatives use the existing canonical `keep_hierarchy` contract on
useful arithmetic leaves, with unique instance parameter identities, the
unmodified keep-reg hook and normal synth/ABC. No production helper changes.
A final native flatten must show all real scalar cells/pins, including inverted
FF QN and any transparent aliases. Attributes are not accepted as evidence that
ABC retained either the equation boundary or acceptable output strength.

**A: pc2/pc4/pc8/pc16 useful boundaries.** pc2 returns the two-bit count
`(carry,sum)=(a&b,a^b)`. pc4 adds two pc2 outputs, pc8 adds two pc4, pc16 adds
two pc8. Preserve the genuine arithmetic outputs at each useful boundary.
To prevent ABC reshaping the larger add into an opaque weak final compound
gate, an even stricter variant retains each HA/FA arithmetic leaf used inside
those count-add boundaries. HA is `(s,c)=(a^b,a&b)`; FA is
`(s,c)=((a^b)^c,(a&b)|(a&c)|(b&c))`. Each output is used by a real count bit.
There are no reset, handshake, register or LUT delay elements inside a leaf.

The exact binary arithmetic inventory is pc8=4FA+7HA and
pc16=11FA+15HA. With a fixed two-input-gate reference (FA sum<=2 levels,
majority<=3; HA sum/carry one), output-bit depths are pc8[3,6,9,10] and
pc16[4,8,11,14,15]. These are structural reference bounds, not native timing.
An unconstrained multi-bit pc16 leaf can still reshape internally and is not
selected merely because its source uses a balanced `+` expression.

**B: retained FA/HA Wallace carry-save population count.** At each compression
level, consume disjoint triples of equal-weight bits with a genuine FA; send
sum to the same column and carry to the next weight. Operate only on bits
present at that level, never consume a same-level incoming carry. Forward
unconsumed bits as wires. Once every column has<=2 bits, use the bounded final
HA chain. The complete count, including the possible16 output, is preserved.
All-input integer identity is `a+b+c = s+2*carry`; no numerical reassociation
or float rounding is involved. All count bits and original zero-extension stay.

| Count | Column-height profiles after compression | Exact arithmetic inventory |
| --- | --- | --- |
| pc8 | [8]→[4,2]→[2,3]→[2,1,1] |4FA+3HA|
| pc16 | [16]→[6,5]→[2,5,1]→[2,3,2]→[2,1,3]→[2,1,1,1] |11FA+4HA|

Taking the shallowest available triples at each fixed level, the same explicit
reference-gate accounting gives pc8 output depths[5,8,9,9] and pc16
[5,10,13,14,14], including the last HA drive function. Source fanout at each
compressor is bounded by the actual roles above. The useful FA leaf contains
two XORs and the majority function; canonical ABC cannot rewrite an eight-XOR
cross-leaf parity chain without violating the same inherited useful hierarchy
contract the original coupon already exercises. Nevertheless final mapped
native structure and SAT are required, not an attribute-only depth claim.

CSA is the stronger next MODEL candidate: it saves four HA per pc8 and eleven
HA per pc16 versus the binary hierarchy and avoids large multi-bit output
functions. It is not approved to build by this document.

## Source-only area, clock and timing admission budget

`structural_model_cells.json` reads exact existing native Liberty area only;
it does not run synthesis or characterize a new path. A representable reference
FA uses2XOR2xp5+3AND2x2+2OR2x2 (7cells,0.69984um²); HA uses XOR2xp5+AND2x2
(2cells,0.21870um²). This is an explicit primitive implementation budget,
not a prediction or upper bound on arbitrary canonical ABC output selection.

| Reference implementation | pc8 | pc16 | This coupon,12pc8+24pc16 trees |
| --- | ---: | ---: | ---: |
| Retained binary FA/HA |4.33026um²/42cells|10.97874um²/107cells|315.45288um²/3072cells|
| Retained CSA FA/HA |3.45546um²/34cells|8.57304um²/85cells|247.21848um²/2448cells|

The whole four-pair/two-quad source contains48pc8+48pc16 useful trees in this
model, reference577.368um² CSA or734.832um² binary. Those replace existing
count arithmetic; do not simply add them and claim measured hardware. For
very conservative planning, retaining the entire measured coupon1086.25374
and adding the whole coupon CSA reference247.21848 gives1333.47222um² before
any strength/extra buffering/placement/tie/clock costs; it is not a physical fit
or canonical area guarantee. FF2616/clock1241.909376fF stay the existing measured
baseline; final candidate native FF/cell counts remain NULL until authorized.

Use the actual electrical burden, not only logic-level count, as admission:
maximum individual count-D source12realFF data pins plus any real local use;
actual final net cap/transition from every native contact; <=32 throughout
all-driver transparent census; per-stage combinational delay<=600ps and TT
setup margin>=30ps with original833/60 setup policy. FFhold/clock/parent/SS and
actual reach remain independent later gates. A source reference depth14 allows,
for example,13 light gate arcs within450ps plus a final useful driver<=150ps;
this is an **admissible budget** (about34.6ps per light arc), not a measured
delay prediction. If final drive takes200ps, the body allowance is400ps; do
not hide that burden. Slew must meet the native320ps limit at every endpoint,
including the shared mask operand Q. Count-D load12 is necessary to test, not
sufficient evidence that those timing/electrical bounds will pass.

Per-leaf canonical ABC does not see the full downstream parent net capacitance
as a native routed network. It may still choose a weak native cell. Thus the
proposed structure remains REFUSED for full build: only ROOT may authorize a
bounded changed source coupon, then its actual all-input source/native proof,
every useful D/operand/input/clock endpoint, area, delay and transitions must
be measured again. A miss triggers another structural model, not a silent
clock relaxation, unpriced pipeline, unchanged route retry or claimed SAFE.
