# HWIN committed-next-address capture mechanism

**PASS bounded memory identity; whole-source calendar/physical HOLD.** No RTL, helper, kit, original gold or gate was changed. This refines region model `21cbb79ac` against exact HWIN `1e057b7bf` / kit `281ec8898`; hashes are in model.json. The 388.8 x604.8um /84-SRAM geometry remains a model, and the original WARN and all nine fanout/93 reach/five pre-pin-FF predicate failures remain open.

## Exact edge origin

Let k denote the state **after** edge k and before edge k+1. M[k] includes the write performed at edge k. P[k] is the current binary event/retire pointer. WV/WA/WD[k] are the wrapper's existing registered write pins (not the new unregistered input word). The wrapper's OLD SRAM plus registered hit/fd forwarding gives original Q[k+1] = WV[k] && WA[k]==P[k] ? WD[k] : M[k][P[k]].

The constructive successor drives the SRAM read address from the **committed Pnext[k]**, computed by the same current adv/radv and registered wrap state that update P at edge k+1. It keeps the actual OLD collision forwarding, with hit evaluated against that next address. Consequently earlyQ[k+1] = M[k+1][P[k+1]]. This is a post-write logical identity made by forwarding; it does not assume the physical SRAM returns NEW data.

A new local plain capture FF uses C[k+1] = WV[k] && WA[k]==P[k] ? WD[k] : earlyQ[k]. Since earlyQ[k] = M[k][P[k]], **C[k+1] = original Q[k+1] at the same edge**, including preceding writes, current writes, adjacent writes, pointer advances, wrap, record/fire collisions, foreign writes and repeated-slot overwrites. The proof uses arbitrary symbolic word values, so it carries due timestamp, user, position, attributes and generation together without guessing their contents. One wrapper each for payload63 and attribute2 per event, and retirement32, needs1,072 capture FF. The gap SRAM remains unchanged.

| At edge k+1 | Original | Candidate |
| --- | --- | --- |
| Memory write | WV[k],WA[k],WD[k] | identical |
| SRAM read address sampled | P[k] | committed Pnext[k] |
| Registered logical head after edge | Q[k+1] | C[k+1], equal to Q[k+1] |
| Following comparator input | current timestamp and Q[k+1] | same timestamp and C[k+1] |
| Retirement and valid update | original due/radv | identical if read identity holds |

There is **no combinational loop**: adv/radv use the old capture FF C[k], original registered eqn/ltn and current source controls. They select the next SRAM address. The new SRAM output reaches earlyQ only after the next clock edge. The old capture FF never consumes that future output in the same cycle. Reading a committed next head cannot evict the current output: the current head already resides in C[k] and the original HEAD_STAGE payload/select FF. A speculative P+1 read without actual adv is not this mechanism.

A wdata-only bypass with unchanged SRAM address is insufficient after pointer advance; its causal mutant fails. Dropping OLD forwarding also fails. No time+1 shift is added: the original tm_event already has the source lookahead. Adding another timestamp increment fails equality at wrap and ordinary dates.

## Calendar consequence and limits

Once the equal-read relation holds, substitution into unchanged source equations gives identical fresh, eqn/ltn, okq/fire/lt, highest-event winner, replay enable, collision pipeline, fd record-clear priority, radv/due, vld/count, RX outstanding image, admission and boot-idle image. All original D>=n+2 configurations therefore retain the same dates under this **conditional source-equation transformation**; n2/D4 and n47/D49 need no extra compare edge. Boot MC/MW decode and five unregistered input predicates are a separate structural repair and remain open. The byte-pinned original test snapshot retains event gold stc+D+2 and collision-fault gold stc+D+3; these constants are checked by proof.py and never inferred from candidate outputs. This packet does not execute the complete RTL or original dated benches and does not mark the22 calendar obligations closed. They are retained individually in model.json.

Initial SRAM contents, earlyQ and C are arbitrary and deliberately unequal in the bounded traces. A first committed read establishes earlyQ coherence, and the next edge establishes C=Q. Source reset holds ks_valid, rec_q, vld and evld low; pin-valid sampling and staged record place first admissible head after this two-edge warmup. The inherited root/group/local release remains edges1/2/3. **Actual per-region release, first-use and no-X guard proof must be performed on the source implementation**, including local asynchronous assertion and malformed/immediate boot/start traffic. No artificial initialization or extra warmup contract is granted. Pointer clear must select its actual reset successor at the read address; it cannot reuse arbitrary adv during reset.

The finite proof checks972 symbolic collision/address cases, all1,127 pointer phases across2..47 slots, and43,608 capture identities after deliberate arbitrary initial mismatch. The phase trace keeps both source start and record holds, while allowing arbitrary committed advances/writes, which is a superset of the actual event control. Causal failures are recorded for no-next-address, no-current-write-bypass, raw OLD without forwarding, extra retirement edge, and extra timestamp shift. The last retirement mutant preserves retire100/start101 occupancy difference; it is a source-rule witness, not an RTL witness.

## Priced mechanism, no hidden fanout waiver

The explicit conservative structural reservation is1,072 plain FF (312.5952um²; TT508.916992fF / FF559.594720fF additional clock pin load),1,072 data mux bits and198 read-address mux bits. Each mux is three native NAND2x1 gates and a slice-local select inverter. Current-write identity is duplicated for every<=8-bit data slice:148 independent six-bit equality/valid predicates, rather than one63-load hit root. Explicit totals are3,810 NAND2,181 INV,888 XNOR2 and1,086 AND2 cells. Actual native TT area coefficients give591.5835um² combinational area. Native library compressed hashes and counts are recorded. These are a proposed explicit implementation's cell areas, **not synthesis or timing measurements**.

For a conservative partial capacity sensitivity, retain every prior2,286FF reservation and additionally add all1,072 capture FF and mux/predicate cells, despite overlap with the prior capture reservation. This gives54.73% of the enlarged band before extra clock/reset/PG/repair cells. A source model must remove duplicates by exact role; no new area ceiling follows. State does not become a runtime-indexed store:33 independent one-word captures accompany the existing real SRAMs. No depth>=3 flop delay chain is introduced.

The adv/radv->next-address mux->SRAM setup path, C->compare/control path and macro->existing-forward-mux->new-bypass->capture path require actual native timing. In particular moving the read address earlier can expose the retire32-bit comparator/advance cone at the SRAM setup pin. All pointer/control/reset fanout must be recounted including upstream roots; each useful predicate copy may itself require source copies. Registered write payload distribution, boot predicate copies, inherited AO21 root, reset groups, all18 regional roots/84 macro clocks, cell PG and access/vias remain open. Extra reset-state cost is zero for plain data capture itself; reset masking and any root/leaf/copy FF needed by the final graph are not zero-cost and are unqualified.

## Next decision

ROOT can select an opt-in source implementation only after reviewing this exact mechanism and assigning complete boot/reset/control source work. Then prove original dated cases and causal mutants on the minimum full mechanism, synthesize the complete native graph, and replace structural counts with actual area/depth/fanout/root loads before any gate. Whole parent slots, PG/OBS/access, clock/neighbour timing and token SU/MU results do not transfer. If this mechanism fails actual source/timing qualification, the fallback remains the **paid complete-calendar redesign**, with D/gaps/RL/start/return/retire/RX/boot and compiler/token deltas derived together; neither +1 output nor old-band rejection is valid.

Reproduce: python3 results/arch/s81_hwin_early_capture_proof_1019/proof.py
