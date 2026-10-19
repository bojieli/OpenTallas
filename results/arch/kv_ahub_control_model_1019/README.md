# AHUB bounded control/reset proposal — MODEL ONLY

Source identity is private component4415ee6cf; source snapshot is evidence, not executable successor RTL. Legal BANK_BITS<=8 is retained: command34 banks (33x8+4), return9 (8x8+4). ABI268 command /68 return unchanged. Public/default bytes untouched. No compiler/helper changes, builds, RTL construction, synthesis or native proof occurred.

## One candidate

Partition command banks into groups8/8/8/8/2, return into8/1. Each physical reset (core and child) owns seven independent kept root synchronizer pairs a0,a1. Exact root equations: asynchronous raw assertion clears both; rising clock while raw high gives a0'=1,a1'=a0. Define group_reset_n = raw_rst_n AND a1. This explicit AND supplies first-edge raw authority; it is not a transparent fanout repair. Each group_reset_n drives both async reset pins of every existing leaf face in its group. The unchanged leaf recurrences remain s0'=1,s1'=s0 with async group reset; unreset synchronous q0'=s1,q1'=q0. Neither q stage is replaced, initialized, or assumed equal.

Within each group compute bank_ready = tx_s1 AND tx_q1 AND rx_s1 AND rx_q1 with binary reductions. group_accept = in_valid AND tx_group_reset_n AND rx_group_reset_n AND AND(bank_ready). Capture one actual group_ingress_valid FF at the original ingress capture edge. Its Q feeds that group's four slot-valid write-D mux inputs per bank (<=32 total). Replace only the redundant per-bank ingress_valid storage with this shared captured authority; retain every per-bank payload ingress, phase, slot-valid, indexed payload, ring_q/ring_valid, landing/landing_valid operation. Whole-word accept is the AND of group_accept. Whole-word out_valid is the AND of bank landing_valid AND all receiver group_reset_n. Accepted history still establishes word identity; no epoch/pass bits invented.

Each group-ingress-valid Q drives FOUR indexed slot-valid write-D mux inputs per bank, not one: eight banks is the maximum32-load group. This correction is why seven admission/reset groups are used. No decoder is presumed to remove those data-pin loads. Receiver group authority enters only one public binary out_valid reduction; it is not fanned into every bank-valid mask.

Healthy admission-to-output remains ingress edge n, indexed write n+1, read n+3, landing n+4. No additional data edge or throughput reduction: one336-bit bidirectional aggregate word/edge. Root synchronization adds two release/admission-authority edges; these must enter actual startup calendars. This is not permission to shift token dates. Group readiness is intentionally stronger during partial startup; full-word acceptance and full-word output remain conjunctions across all groups.

## First authoritative use, assertion and repeat reset

Consider raw alreadyLOW at first sampling with every root/leaf Q, valid and phase arbitrary, including all1. Every group_reset_n is0 combinationally from raw, irrespective of a1. Therefore all group_accept and public accept are0, and receiver public out_valid is0 BEFORE NBA. Any old payload/ring/landing activity at that first edge has no authority. Root and leaf async state then clears through actual reset network; subsequent clock edges clear phase, slot_valid and ring_valid while leaf s1 is0. No delayed programme, fixed quiet interval, initialized storage, equal-Q premise or assertion of acceptance before qualification is used. External raw-low remains the authority even if a simulator seeds old async-Q after its initial reset event.

Equality argument: after a genuine raw-low assertion or the first raw-low sampled edge, root a0/a1 are cleared independent of their old values. Every group_reset_n remains0 throughout the root two-edge release chain, so all leaf asynchronous s0/s1 are cleared. During those same common-clock edges, every unreset leaf q0/q1 acquires0. Thus before any leaf s1 can rise all leaf q states and ring reset histories have converged by recurrence, not by initial-Q assumption. Common raw reset and common clock then produce identical reset readiness in every bank at the earliest authoritative capture. At that edge group_accept equals every constituent original bank_accept; after convergence it remains so until reset assertion, which immediately removes group authority. Any arbitrary/partially primed state before convergence is blocked. This is a conditional common-clock/reset proof obligation, not a claim about unrelated native leaf clocks.

On raw release, roots require two rising updates for a1; leaves require their original two s updates plus two q updates. Acceptance uses PREEDGE values. Relative to the original leaf chain, earliest qualified capture is delayed exactly two rising edges; a source implementation must retain this edge/NBA relation, not infer it from a numeric arm counter. At the edge leaf s1 rises q1 has already been driven low by s1=0 history; phase/slot validity have cleared. Local qualified and regional-ready predicates still control actual writes/read validity as in the frozen source.

On receiver reset, public out_valid immediately loses raw authority; leaf landing_valid asynchronously clears through group/leaf reset. Previously accepted receiver-owned words may be discarded exactly as in the frozen conditional component contract. A transmitter-only reset blocks fresh admission but does not clear receiver phase/slot state: already accepted words continue to drain. Because core reset is command-TX and return-RX (and child reset is opposite), do not reinterpret independent resets as a whole-engine flush. Root release adds no new cancellation channel. Assertion pulse width, combinational reset hazard avoidance, async recovery/removal and running-clock requirements are native obligations. This proposal does not certify legal whole-child startup or retained fault retirement.

## Explicit all-driver equation graph

This is a proposed bounded logical implementation, not a source syntax inference. Synthesis must retain this shape or fail its audit. Binary trees implement all conjunctions/disjunctions; no reduction root drives its whole input tree. BUF/INV-transparent nonclock loads are counted together. Each inversion below has only the stated local consumers.

| Root class | Maximum actual consumer pins in proposal |
|---|---:|
| raw physical reset |14 root async pins +7 group-reset AND pins =21|
| root a0 / a1 |1 /1|
| group_reset_n |16 leaf async pins +1 group admission +1 receiver output-authority reduction =18|
| in_valid command / return |5 /2 group admission pins|
| leaf tx s1 / q1 |q0 and bank-ready / bank-ready =2 /1|
| leaf rx s1 |q0, bank-ready, local reset predicate, landing-valid async =4|
| leaf rx q1 |bank-ready, local reset predicate, landing-valid sync clear =3|
| bank-ready / binary reduction nodes |1 each|
| group_accept |group-ingress-valid D + public-accept reduction =2|
| group_ingress_valid Q |four slot-valid write-D mux inputs per bank (<=32 total)|
| binary phase bit incl inverse |<=6 (four decode polarity uses plus next-phase logic)|
| each shared four-way phase decode |1 write-enable AND +BW read-data AND +1 valid-read AND <=10|
| qualified per-slot write enable |BW payload write muxes +1 slot-valid write mux <=9|
| local ring-active reset predicate |4 write-enable AND +BW ring_q hold mux +2 phase clear mux +4 slot-valid clear mux +1 ring-valid clear mux <=19|
| ingress payload Q |four per-slot payload write-data mux inputs =4|
| each indexed payload cell Q |own write-hold mux +one read AND =2|
| slot_valid Q |own write-hold mux +one read AND =2|
| read-data AND, binary OR nodes |1 each|
| ring_q / ring_valid |one landing D /one landing-valid D|
| landing payload / landing_valid |one ABI output /one binary reduction input|
| tie-high groups |<=32 leaf/root s0 D pins per independently placed tie source|
| tie-low groups |<=32 synchronous reset-D mux pins per independently placed tie source|

Phase decode implementation is explicit: decode binary phase into four one-hot terms; rotate decode by two for read_slot, preserving READ_OLD. Write/read decode share terms, with their combined loads counted above. Increment phase via inversion/XOR, no extra phase FFs. Indexed payload is not shifted. Decoder and mux graph must be emitted without collapsing replicated banking into a wide select root. Primary payload inputs each drive exactly one ingress FF. No integer-loop reset masks or shared scalar selects may be introduced. Ties require independently realized local cells, not a shared constant wire driving hundreds of pins. Physical clock is a separate distribution network:1731 non-array state sinks plus actual memory-clock pins; if payload is FF-expanded there are3075 sinks. A bounded clock tree with32 sink loads needs at least55 or97 leaf buffers respectively, then2 or4 intermediate branches plus root. These are lower bounds, not a CTS solution or phase proof.

The maximum nonclock load in this explicitly stated graph is32. Native audit remains HOLD: no mapped graph exists. It must include all comb/input/tie/reset/macro roots and transparent BUF/INV aliases, both Q/QN polarities, actual merge behavior and constants. A clone annotation alone is not evidence of preserved independent root pairs.

## Full incremental cost and traffic

Indexed payload1344 + ingress/read/output payload1008 + phase86 + slotvalid172 + ringvalid43 + landingvalid43 + group-ingressvalid7 + leafreset344 + rootreset28 =3075 bits. Existing3083 minus36 redundant ingress-valid FFs plus28 real root FFs =-8. Non-array state1731 bits. No arithmetic MACs/cycle added. Four indexed slots per bank, one336-bit aggregate write and one336-bit aggregate read each edge across43 banks; four-slot READ_OLD/separation2 remains a genuine indexed requirement. Input and output boundaries each336 bits/edge plus4 public valid/accept outputs and2 input-valid controls. No memory initialization/reset ports.

All28 added root FFs require actual clock and PG contacts;36 removed FFs also change those loads. A flop-equivalent bit delta is not area savings: memory realization, reset cells, mux/decode gates, tie cells, clock buffers, routing and power distribution are unpriced. 43 read/write banks must be explicitly bound and counted. No suitable macro receipt, area, pin pitch, TT/FF arcs, collision behavior or PG ownership exists here. Depth4 must remain true indexed storage and receive real SRAM binding in a native successor, not a four-stage shift rename. 1344 payload bits being below2kb does not qualify the memory technology.

## Exact gates before construction/adoption

ROOT must approve new raw-authority/reset hierarchy and +2 startup edges. An opt-in private source successor must preserve defaults and actual4edge accepted-word behavior, prove arbitrary-state first use (including raw alreadyLOW before first edge), partial group startup, independent/repeated TX/RX resets with outstanding words, earliest legal release capture, four-slot wrap and no extra output/capture. Mutants must remove raw authority, advance root/leaf release, merge or overload reset groups, accept stale group valid, shift read slot, and misattribute return fault ownership. Preserve all failed controls. Then audit exact all-driver mapped graph, bound true storage, clock/PG/pin/macro contracts and actual per-link reach<=405um; TT setup and FF hold>=0, TT/FF spread<=80ps, local contacts<=6/um. Existing6positive/27mutant component results cannot qualify this unimplemented proposal.

ZH/reciprocal arithmetic/source overlay, real retained-health pass/fault lifetime, child reset contracts, RY1 versus RY2/RS1 adapters, actual source calendar/SU-MU token price, native access/OBS/PG and whole-parent source-safe qualification remain separate HOLD. No map/fullshell grant or qualification flag is implied.
