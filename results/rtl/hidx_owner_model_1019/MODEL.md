# HIDX whole ownership successor — MODEL, build refused

Exact source remains `5af00a1ab`, SHA256
`35633c534dbe6236bbbc9074af1e3cf0eb07a2d7e5e6d3b3bee75d0e7652fabf`.
This packet changes no RTL, source parameters, compiler schedule, physical kit,
gate, or acceptance rule. The current 3072-record/1282-edge miter, historical
+5 interface age, and causal mutants 7/8 remain the existing proofs, not proofs
of the architecture below. ROOT review is required before even the bounded
source prototypes proposed at the end. Whole-tile build remains REFUSED.

## Exact current graph, every role

The r3 mapped SHA is
`6aafe33bacb8ca1464ee6c9bd1ad3fb2b622e52cd6336600b1adea413cbf8684`.
`owner_index.jsonl.gz` contains **all 113,836 nontransparent drivers**, not a
worst-N sample: 83,804 combinational, 23,532 FF, 4096 macro output pins,
2402 top inputs, and two literals. Native source input nets, native master,
all source aliases except repetitive distribution aliases, endpoint role
counts, and source net identity are retained. The immutable full endpoint
ledger retains **every actual sink pin** remotely, including all transparent
aliases. `artifact_manifest.json` hashes both it and the compact index.
An omitted endpoint list in the compact index is a size optimization, not a
fanout exclusion. Follow its exact driver in the full ledger or original map.

The strict native scalar oracle still **REFUSES the original SRAM bus**.
This is the independently expanded, exact-Liberty-bus DIAGNOSTIC only.
No native or physical SAFE claim follows. No name-based clock exclusions
were used; the source census removes actual native clock-role pins only.

| Current unsafe source family | FF roots | Comb roots | Ownership to replace |
| --- | ---: | ---: | --- |
| Rotate total | 960 | 6 | Wide selects and shared `total_nx` D |
| Pair count | 95 | 12 | Registered selects plus group popcount D |
| Quad count | 50 | 10 | Registered selects plus pair popcount D |
| Half count | 59 | 6 | Registered selects plus summed-count D |
| Partial carry | 42 | 3 | Bank selectors and next-bank D |
| Write formation | 6 | 0 | Shared total/fill upstream |
| Mask count/enable | 8 | 0 | `s3_n` and `s3_v` broadcast |
| Emit | 0 | 2 | Control-ring age decoder D |
| Reset | 1 | 0 | Final face reset drives 1757 real reset pins |
| Total | **1221** | **39** | No unclassified unsafe functional root |

The two literal roots separately drive 5896 and 2997 logical pins; their
physical tie ownership is still HOLD. Native macro outputs max1 and inputs
max25 do not qualify the other roles. In particular, INV/INV distributions
remain transparent. Pin-reg declarations do not prove that synthesis retained
constant output pin FFs: 900 low and 40 high output endpoints remain attached
to literals in this graph. Their exact pin/constant policy needs ROOT review;
no blanket registered-output claim is made here. `clk_mem[7:0]` is not a set
of eight implemented SRAM clock domains: the source connects every macro to
`clk`; the unused ports do not qualify a regional clock plan.

Exact native FF accounting: 21,773 DFFHQNx1 at 0.2916 um²/0.474736 fF CLK
and 1759 DFFASRHQNx1 at 0.37908 um²/0.462899 fF CLK. Total FF area is
**7015.80852 um²**, clock capacitance **11150.666269 fF**, before eight
macro clocks and CTS. Total current standard area is 15497.41734 um².

## Proposed functional ownership, same data ages as a hypothesis

Use four payload bits per owner, **with complete useful D producers and
upstream operand copies**. Do not instantiate the current `dist` helper.
Unique kept functional paramods must survive native mapping; any merge or
transparent alias invalidates the claimed partition. The following are
equations and exact source-array capacities, not a mapped PASS.

1. **Compaction:** a group/payload-slice owns ONE eight-bit pin mask, shared
   across its eight output slots, instead of eight independently copied masks.
   Nine 4-bit slices per 36-bit record give 8*9*8 = **576 mask FF**. For lane k,
   `prefix[k]=popcount(mask[0:k-1])` and
   `pick[s,k]=mask[k] && prefix[k]==s`; output bit j is
   `OR_k(pick[s,k] && payload[k,j])`. Preserve input lane order and zero slots.
   Compute the prefix/pick predicates locally, with balanced popcount depth;
   each pick owns four actual payload ANDs. Each local valid bit serves only
   its own prefix and decode logic. Native prefix sharing, internal fanout and
   <=600 ps/20-level depth must be measured on the bounded source coupon.
   A linear combinational prefix carry chain is not presumed acceptable.

2. **Pair:** PN=16*9=144 four-bit payload owners per pair. Partition the 144
   selector FFs per count bit into six useful `pc8` D producers, 24 FF sinks
   each. Four pairs require 4*144*4 = **2304 selector FF**. Each producer has
   its own registered input-mask operands; it is the actual popcount equation,
   not a copied alias of the shared old `gcnt` output.

3. **Quad:** QN=32*9=288 owners per quad. Twelve independent `pc16` producers,
   24 FF sinks each, recompute the sum of the two original eight-lane counts.
   Two quads require 2*288*5 = **2880 selector FF**. Do not reuse the pair
   producer's output as a new 288-load D source.

4. **Half:** HN=64*9=576 owners, 24 six-bit sum producers with <=24 FF D
   sinks each. These producers read distinct same-age S1 pair-count operands.
   Reserve 2*24*5=240 S1 operand FF, plus 4*5=20 independent operands for the
   canonical/low-count path, **260 S1 count FF** total. Preserve old group
   count arithmetic, zero-extension, slot order and simultaneous pair+quad
   stage. Half selectors are **576*6 = 3456 FF**.

5. **Rotate/total:** 576 payload select owners plus 64 one-bit mask-rotate
   owners, **640*6 = 3840 FF** total. Each existing-age selector becomes an
   actual local modulo-64 recurrence, with local increment operands:

   `T_i_next = s3_valid_i ? (T_i + n_i) mod 64 : clear3_i ? 0 : T_i`.

   This is exactly the low six bits of the canonical ten-bit total under the
   same reset, same inputs and priority. Keep canonical full total/overflow
   fault behavior; never substitute local low bits for fault/selected_count.
   These FFs own their own arithmetic D, so a shared `total_nx` no longer
   drives 640 copied D pins. Group at most eight recurrence adders per S3
   increment operand bank: 80*6 = **480 extra S3 increment FF**. Their upstream
   summed-count functions have ten six-bit S2 operand copies per half:
   10*2*6 = **120 S2 FF**. Canonical count/overflow signals remain separately
   owned; local modulo-64 arithmetic must also mirror faulted execution.
   Native adder carry/input fanout must include both polarities and feedback.

6. **Input-mask upstream budget:** per lane, nine compaction copies, six pair
   producer copies when its group is even, twelve quad producer copies when
   its group is 0/1/4/5, and one S1-count producer copy. The worst lane has
   **28 real pin FF sinks**, including the four old kept valid copies reused
   inside the nine. Counts by group are 28/22/16/10/28/22/16/10, each over
   eight lanes: **1216 valid pin FF** total, including the 576 compaction mask
   FF. Do not add the old four copies again. This is a source grouping budget;
   all input native pins and any preservation-induced copies must be censused.

7. **Valid and clear:** shared `s3_v` cannot drive 640 six-bit recurrences.
   Twenty-seven input owners, each with an independent W=1 five-slot ring,
   supply up to 24 *independently decoded useful* age3 predicates. Each
   predicate owns one recurrence's six-bit update, not a transparent relay.
   Raw input drives 27 new pin FF plus the canonical pin FF, <=28. Slots/onehot
   pointer each serve at most 24 local decoder inputs plus write/feedback;
   native pin count, reset, arbitrary-state convergence and exact age3 still
   require proof. Remaining four decoder slots can own four 16-bit mask-enable
   chunks. Duplicate this structure for clear: **2*(27+27*10)=594 FF** reserved.
   These are coherent five-slot rings with one write/edge and fixed taps,
   not >=3-stage flop delay chains or a partitioned indexed large store.

8. **Write/carry:** 64 records*9 slices*6 = **3456 write-control FF**. Each
   samples an assigned local T_i Q, retaining the OLD prefix age; those Qs
   also own their recurrence and a four-bit rotate select. For carry,
   `next_bank=((T_i+n_i) mod64)[5:3]`, algebraically identical to
   `(f0[2:0]+nsum[5:3]) mod8`, with the original mutant-6 perturbation retained.
   The shared D is removed by assigning 72 carry slices to independent
   recurrence producers; **72*3=216 bank-select FF**. Each four-bit payload
   slice owns an eight-bank data/mask selection and the original 288-bit
   partial flit remains one coherent carry object. No old full 2304-bit W
   array is reintroduced. Preserve read-before-update of carry and every
   original same-beat write role. Native D and bank-Q mux fanout remain checks.

9. **Emit:** recompute the actual age5 ring read equation in eight kept useful
   decoder owners, <=24 existing enable-copy D FF per owner. Four local age5
   group-bit decoder owners supply <=24 group-copy D FF each. Each slot/pointer
   FF serves the decoder ANDs; no copied final OR/buffer output is distributed.
   Preserve all canonical ring ages and metadata rank/group/gbase equations,
   SRAM read age, four outputs, `read_v`, tx hold when not enabled, and fault
   clear behavior. Audit every decoder input, not just its 24-load output.

## Reset: explicit new protocol proposal, not inherited phase proof

Original face is two asynchronously asserted FF with sampled release. Keep
that exact face, then propose 16 first-level and 256 second-level retained
asynchronously asserted reset-carrier FF. Each carrier has D=1 and parent
reset on its native asynchronous reset pin. Face output drives16 reset pins;
each first level drives16; each final leaf drives at most24 functional reset
pins (eight-load reserve), total capacity **6144 functional reset endpoints**.
This is **272 extra FF** and a real two-level assertion/release topology,
not a BUF/INV network. The external reset still drives only the two face FF
reset pins. All carrier clock loads, parent reset pins and tied D inputs count.

Release becomes face2 + regional2 = **four sampled edges**, so propose
**+2 reset/POR guard edges**, separately from per-token latency. No compiler
or guard change has been implemented. The tree has extra physical assertion
propagation and recovery/removal/pulse requirements, even though ideal RTL
assertion cascades asynchronously. Prove the original assertion type, narrow
pulses, every phase, stopped/restarted clocks and no early use against the
new explicit guard. Do not describe its waveform as identical without proof.
If actual reset endpoints exceed6144 or any upstream source exceeds32,
resize/reprice the whole topology before source. Native clock/phase and reset
physical reach are not inferred from this logical branching arithmetic.

## Storage and physical cost: independent release holds

The eight current 64x512 SRAMs have unsafe physical faces (795/792 contacts
over77.784 um) and unqualified OLD/readclock/repair/access. No control change
repairs that. Keep their source immutable until an exact storage proof exists.

Two concrete genuine-SRAM alternatives are recorded, neither adopted:

* **80-bank no-depth-reduction option:** 8 logical banks *2 depth halves *5
  64-bit width slices of dual-clock32x64. All64 old addresses remain available;
  two depth halves require sampled read-depth ownership and a 288-bit read
  select per logical bank, plus one-hot write-depth decode. Both depth halves
  must retain read-disable hold and the original same-address OLD behavior.
* **40-bank address-bound option:** the exact source's write address is
  `{1'b0,fr[7:3]}` and read address `{3'd0,grp5[3:1]}`. Thus write bit5 is
  always zero and reads are0..7, even without a legal-programme assumption.
  Five32x64 slices per logical bank cover all32 reachable write addresses.
  Existing write bits288..511 are literal0; every read consumer uses only
  bits0..287. Repair controls are fixed disabled in this top. These are exact
  source equation observations, **not** authorization to shrink the macro:
  prove all-input/fault/wrap/reset behavior, low288 identity, masks, repair
  contract and OLD collision semantics before accepting any bit reduction.

80 banks provide163840 physical bits and160 clock contacts; 40 provide81920
bits and80 clock contacts, versus original262144 bits/eight clock contacts.
Clocks are counted twice per dual-clock primitive even if tied to one logical
source; phase/clock-tree cost never disappears by tying clocks in a bench.
Useful old capacity is not guessed from successful traces.

The historical 32x64 coupon reference footprint31.992*17.304=553.589568 um²
would give44287.16544/22143.58272 um² raw macro area for80/40 banks. These
numbers are **reference budgets only**: the current SC2 prototype19ccd29b9
has no production Liberty/minimum-CQ acceptance; conditional transition work
is not native admission. Exact generated LEF/PG/contact/OBS/repair and timing
role fingerprints must replace this reference before any build. No GDS or
transistor-layout claim is made.

An illustrative full43.2-lattice arrangement uses ten columns, five width
slices per depth or logical-bank group, paired above/below a full-width band.
With the historical footprint, 80-bank outline432*475.2 and 40-bank
outline432*302.4 have a **432*129.6 =55987.2 um²** standard band. A different
qualified macro footprint invalidates this packing. At40–60% the band admits
22394.88–33592.32 um² of mapped standard cells. The outline diagonals exceed
405 um, so this is not a reach proof: bit-slice placement, regional clocks,
all stage paths, macro-face buses, clock landing and PG channels require an
actual model before placement. Parent slot regrant is NULL. No fit is claimed.

## Whole budget and review boundary

Literal candidate families above reserve **19094 FF**: selector12480,
valid-pin1216, S1count260, S2count120, S3increment480, valid/clear594,
write3456, carry-bank216, reset272. Some replace old FF; do not add them and
call the result measured hardware. For a deliberately conservative admission
ceiling retaining the entire old graph as well, 23532+19094=**42626 FF**.
At the maximum cited native FF area0.37908, the added FF ceiling is
7238.15352 um²; base standard area plus this is **22735.57086 um²**, before
new useful combinational predicates, ties, depth-decode/read mux, pin-retention
repair and CTS. Added FF clock cap is bounded by19094*0.474736=
**9064.609184 fF** for the cited positive-edge FF choices; actual typed mixture
must replace the bound. This is not an electrical capacitance limit or a
qualification of macro clocks.

Remaining source-control combinational area/depth, tie policy, final mapped
FF replacements, native macro clocks/access, clock regions/landing and all
parent costs are **NULL**. Therefore the full model is **REFUSED for build**.
The standard band leaves at most10856.74914 um² at60% for all those standard
cell additions after the conservative FF ceiling; their fit is not asserted.
Same-age functional copies hypothesize zero per-token added edges, but
regional crossings/physical reach may require a nonzero delta. Final compiler
latency is **NULL**, distinct from the proposed +2 reset guard.

ROOT can separately review these bounded default-off source coupons:
1. One group/nine 4-bit compaction slices plus pair/quad producer cohorts;
   all256 lane masks, arbitrary payload and original order/zero equivalence;
   wrong-prefix/order/merge and dropped-copy causal negatives; every native
   FF/comb/input pin, no transparent exemption, and actual depth.
2. One24-owner local counter cohort with eight-way increment ownership,
   ring-derived age3 valid/clear, write-old-prefix and carry-next-bank; all
   count0..64, wrap/clear collisions, arbitrary old state/reset phases and
   original mutant7/6 causality. Include every upstream producer's input cone.
3. Whole reset topology/source endpoint census, narrow/stopped-clock pulses,
   exact +2 guard and native pulse/recovery/clock costs before integrating it.
4. Exact40/80-bank all-input storage equivalence against the original source
   with qualified macro models, fault/wrap/repair/collision/disabled-read
   negatives. No synthetic D-1 or free same-address NEW substitution.

Only after those coupons and a fully populated area/clock/storage/latency/
parent model may the full source be rebuilt. Only after full3072-record,
default byte-identity, all mutants, real boundary/register/lifetime and strict
native scalar evidence may ROOT consider physical gate review. No duplicate
8891-second synthesis, full array simulation, or gate was launched here.

## Reproduction and pickup

Immutable source/cache: ot-agidock128,
`/srv/opentallas-scratch/claude/codex-hidx-safe-copies-r3-1019`.
New analysis lives in `owner_model/`; full all-pin ledger and unsafe equations
remain there and are SHA-pinned by `artifact_manifest.json`. `inventory.py`
reads only the cached map and prior explicit-bus diagnostic; `compact.py`
adds native SEQ area/clock accounting. Run with unpinned `ot-run`, measured
8GB/one thread and4GB/one thread respectively. Final units1962798 and1963389
both ended exit0. Those exits mean collection completed, never design PASS.
