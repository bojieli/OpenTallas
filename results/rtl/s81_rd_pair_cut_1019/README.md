# Bounded typed V row-pair and local-copy mechanism

The actual minimum cut PASSES: two existing XR/rstop blocks, three actual VP
blocks and six real native512x128 SRAM models. The default-off define is
OT_S81SL_RD_PAIR. The selected source is241f7b963; final fixed-calendar bench
020c90875. This is a transport mechanism/pricing proof, not production admission.
Full4480-pair/480-peer architecture model remains7b4c7ac91; root_merges has an
explicit hold on importing source RTL before exact timing-contract/regressions.

The preferred V format is273 bits: valid1/type3/leaf3/even-row10/data256; the
physical direct V partner is the destination. Source config validates that the
mask names its actual sid XOR1 partner. Existing source SRAM RDOUT pairs stream
through existing registered paths; the receiver writes each as a complete row
pair. Local copy uses registered CI feedback INSIDE XR into the existing RD
classify/unpacker, reading and rewriting actual SRAM even for different leaves.
No global ready/backpressure, runtime waits or numerical conversions are added.
The only bench wait triggers reset fault injection after the first pair enters
the receiver; production commands use fixed pin cycles.

functional_stress/mut_0.log proves64 four-pair messages every5edges (256pairs)
and64 two-pair messages every3edges (128pairs), all384 subsequently read back
exact from actual SRAM, plus isolated4/2-pair V, different-leaf local copy,
reset/abort/drain/restart and exact component edges. All11 causal wire negatives
FAIL: missing, duplicate, row, leaf, data, type, partial, late, RD/V collision,
wrong destination and missing reset. The static checker detects missing/late/
duplicate/partial data; this does not claim new hardware message authentication.
The hardware collision/malformed/config checks remain separate sticky faults.

throughput_receipt.json records actual first source CTL pins and last XR sw
pins. Startup-inclusive256/340=.75294 versus.8pair/edge and128/212=.60377 versus
2/3 are both within10%. Their write spans319/191 exclude startup; no host or
other-owner traffic is hidden in those component prices. Exact42-file shipped
source inventories match the pinned commits. functional_first preserves the
first rstop-mux design and default-off legacy XR6000-cycle / rstop16-stop144-check
PASS; functional_loop preserves the final local loop source before throughput.

component_receipt.json names every origin: source line CTL pin→XR c_v/VP command
input5; VP command input→VP lo output5; VP lo output→V output5; V INPUT→XR sw
output/VP sw INPUT6; local CI→XR sw/VP input3. sw is NOT the internal SRAM write
edge. Actual slice DL4 command/lo/sw glue, V landing/phase, internal macro write,
host and PHY/peer ages remain independent composition terms. Global XR2=7 has
a different origin; no existing timing constant/whitelist was changed.

Canonical main59835e962 run_abi3_physical.py, pinned Yosys0.68/ABC and TT ASAP7
liberties ran synthesis only. All records say NOT_EVALUATED for engineering
acceptance because no timing-bearing stage ran. size_summary.json preserves:

- XR baseline15918FF/7620.73272um2; selected internal loop15925FF/7924.55076um2.
- Rstop baseline15521FF/7355.79954um2; loop15521FF/7386.35922um2. Its RTL is
  byte-identical to the original. The small area/cell difference is mapping
  order variation from parsing the different selected XR, not new rstop logic.
- Rejected first local-delivery rstop mux16552FF/7913.79072um2 (+1031FF) is
  retained. It broke sharing between gather and delivery payload registers.
  The internal loop eliminates that wide payload unsharing: +7 semantic FF
  per slice, no new SRAM or standalone1104-bit retention. The prototype does
  NOT implement the originally estimated kept control distribution; sizing
  that safe successor is still required.

The measured combined standalone area difference334.37772um2/slice would be
21400.17408um2 across64 slices BEFORE safe-control, physical clock/reset or
routing/slot costs. This is not a hardened area or a production delta.
Mapped census includes complete internal cell pin directions and grants no
fanout waiver: XR loop38Q and96total driven nets>32, max1425; rstop9Q and57
nets>32, max1896; raw reset input loads3/2505 respectively. External output-port
loads are not counted, so these are already-failing internal lower bounds.
Source reset/data control roles still need proper restructuring. No gate is
ready. Exact raw fanout JSON, stats, synth scripts and immutable canonical
records are in sizing; full netlists/objects remain on the fleet.

resource_binding.json applies component observations to all5031 proposed data
submoves. The XR lo selector is SHARED by five leaves: busiest rank0/sid5 needs
1030pairs, so the complete payload bandwidth floor strengthens520→1030edges.
The uncoalesced V reference costs692edges at its busiest source. Control
occurrences/85jobs are reference costs before possible proven broadcast
coalescing; they are not universal lower bounds. Actual per-path calendars,
leases, other traffic,883 unlanded traversals, qualified native/peer ages and
full-token delta remain OPEN/NULL. Gain/G8/NX/XB/head are unchanged gaps.

No gate, REVIEW, submit, timing mask, uncertainty change or main edit occurred.
See NEXT.md and SAFE.md before any further implementation or physical work.
