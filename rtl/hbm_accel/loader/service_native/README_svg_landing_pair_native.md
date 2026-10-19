# Repeatable native landing/pair leaf

`ot_hbm_svg_landing_pair_native #(.J(j))` is an opt-in four-macro hardening
vehicle, j0..3. Model63cdbc115 preceded RTLb7043ae12. Final component bench is
10e6d5a53. Existing masters remain unchanged; no gate, REVIEW, SDC or submission
is included. `hbm_svg_landing_pair_native_model()` exposes the analytical model.

## Source and native roots

The leaf instantiates two native `ot_hbm_svc_sm8_landing_boundary` banks J/J+4,
one kept pair select, one group-alignment ring, and the entire selected return
ring. The actual storage is two256x256 landing SRAMs and two8x285 dual-clock
response SRAMs,22577.762304um2 total. Each landing macro packs four64-row blocks.
The component miter also instantiates two original landing masters as references;
those two reference SRAMs are not part of the four-macro leaf inventory.

All three roots are explicit: `pair_hbm_clk`, `pair_clk`, `return_clk`, with
corresponding active-low raw resets. Both banks use the same pair HBM/stream
roots. Old `bank/4` clock mapping must be replaced for banks J and J+4.
Each native bank owns its two-stage HBM/stream reset landing; feed it RAW reset,
not the leaf's landed reset, which would accidentally add two more stages.
Pair/meta and local-return logic each have their own two-stage reset landing.
Reset assertion/release must be balanced across the three roots and other
participating pair/cache roots. No payload reset mass is added.

The entire ringSlice, including source slots/write pointer, return-root read
pointer/mux and registered output Q, stays in this source leaf. It exports
registered data256+ordinal3+valid1+phase-fault1=261signals. No read-select
feedback or combinational fault OR is exported. Native ready, overflow,
completion bank and bank fault pins are connected directly to their existing
registered Q, separately for each bank.

## Exact interface

Ingress bank b0/1 carries native bank J/J+4. `in_data[b*285+:285]`, `in_v[b]`,
`in_ready[b]`, `overflow[b]` use the HBM root. Shared `reserve_v/bank/epoch/total`
and `stop` are pair-root pins. Read controls are separate:
`read_v[b]`, `read_bank[b*2+:2]`, `read_row[b*6+:6]`.
`complete_v[b]`, `complete_bank[b*2+:2]`, `bank_fault[b]` are pair-root outputs.
`ordinal[2:0]` and `group_valid` are pair-root inputs. `out_data`, `out_ordinal`,
`out_valid`, `phase_fault` are local-return-root output Q.
There are632inputs and273outputs,905pins total; shared reserve/stop saves32pins
against the earlier conservative duplicated-control budget.

`group_valid` is INDEPENDENT of both read enables. Partial/final drain groups
may leave an unused bank's SRAM output unchanged while all four pair group
valid/ordinal envelopes remain aligned. The separate parent metadata ring
carries the mask and discards unused data. This leaf never derives group
validity from the selected read enable, stop, arrival, ready or credits.

## Metadata and latency

The group ordinal/valid passes through an actual four-slot, four-bit ring with
three-edge latency (write0/read2), aligned to the native SRAM output Q.
Pair data/control captures and selected output take two further edges. The
actual four-slot tagged return ring takes source write plus local-return Q.

| Edge after external launch E0 | Leaf event |
|---|---|
| E1 | Native read/control pin capture; group metadata ring write |
| E2 | Actual landing SRAM read |
| E3 | Native read-data output Q and aligned ordinal/group-valid Q |
| E4 | Pair captures both native read outputs and metadata |
| E5 | Registered local 2:1 selection |
| E6 | Write selected data/ordinal/valid into actual return ring |
| E7 | Local forwarded return-root output Q |

Leaf request-to-return is seven capture edges. Cache native capture plus
rotate2/rotate1 adds three, hence request-to-final-cache ten edges. This does
not add a new price to the existing parent model: native read +2 over the old
one-edge SRAM read is already in the native8edge price; regional return7edge
price already contains pair2+return2+cache3. Compiler prefetch remains15edges.
After balanced raw reset, first accepted pins are E3; first returned valid
can be E9. Unread startup data is masked/ignored; no power-up SRAM data claim.

Bench clocks are HBM1024ps, pair834ps phase30ps, return834ps phase10ps. Normal
pair-to-return setup interval is814ps, next-launch hold offset20ps, and local
return-pointer-to-output setup is834ps. These are ordinary one-edge paths;
ring epoch tags never authorize multicycle or false-path exceptions. Actual
wire/clock insertion and TT/FF timing remain OPEN.

## Actual-SRAM component proof

Fleet Verilator5.050, ot-epyc6, source10e6d5a53. All four J0/1/2/3 instances
pass independently at production LBANKS4/RESPONSE_DEPTH8. Each fills four
272-sector blocks, reads every ordinal0..271 for each landing block across
three reset epochs, includes bubbles, stopped/full FIFO bursts and occupied
resets, and exercises1032 group-valid cases with selected read disabled.

Each J passes3264 payload groups plus24 masked warmup groups,825 admitted
packets (including reset-flushed packets and duplicate witness),12 completions
per bank, first-valid edge9 in all three resets, and every measured payload
launch-to-return delay exactly7edges. Twelve windows each sustain64 groups in
64 pair edges,32payload bytes/edge. Original-master miter reports0/0errors:
externally accepted packets are independently score-boarded then replayed at
the native FIFO write edge; core ready, identity/order, completion/fault and
actual SRAM read outputs are compared with the original masters.

Mutant1 inverts pair selection: PAIR_SELECT_DATA_FAIL (3263errors).
Mutant2 shifts the group metadata ring by one: PAIR_META_ALIGN_FAIL (4276).
Mutant3 reads the wrong tagged return slot: PAIR_RING_PHASE_FAIL (6653).
All mutants retain0/0bank-master miter errors, isolating the return mechanisms.
Witnesses and machine-readable summary are in
`rtl/test/hbm_accel/svg_rel/native_pair_evidence/`.
The initial static-producer testbench race is preserved as a diagnostic log;
10e6d5a53 fixes its concurrent task locals. No RTL fix was needed for the miter.

## Pre-gate checklist

1. Fixed at source: all native payload/control pins enter or leave Q, two-stage
   reset landing per root, no data reset mass or combined combinational fault.
2. OPEN: reduced380.16x198.72 geometry has382.604um cell-band diagonal; actual
   pin-to-register, macro, return-Q and local net reach <=405um still unmeasured.
3. Fixed at return slices: kept16-bit selects/pointers. Native bank epoch/seen/
   count controls, reset distribution and mapped preserved copies need audit.
4. Fixed seven-edge pipeline, no pin bypass. Normal one-edge paths need mapped
   logic-depth and directed setup/hold analysis.
5. Source PASS: four actual SRAMs;1140bit ingress rings/bank,1052bit return ring,
   16bit metadata ring. No >=3-stage unchanged flop metadata chain.
6. Geometry candidate only: four43.2-lattice macro origins; one full-width narrow
   cell band inside43.176um gap, height from measured cell area at40-60%; routing/
   PG/clock access reserved elsewhere. Synthesis/native pin-access audit OPEN.
7. Three explicit roots; physical forwarding, native neighbour references,
   TT/FF pin-flop spread<=80ps and hold margin>=0.03ns remain OPEN.
8. Static schedule/group-valid independent of reads preserved; parent mask and
   15edge prefetch integration remain necessary before production qualification.

The separate packed-row-cache4096bit assembler is outside this leaf and remains
a storage blocker. This source leaf does not imply whole-SVG physical closure.
