# Source-bound XFIN SRAM model (MODEL ONLY)

Baseline actual source0618133cbc, ot_s81dv_xfin NS16/NVL5/LM5/LA6, four ENG finish instances (three trees each) and one NORM tree. No RTL, synthesis, simulation or physical run is part of this packet. model.py statically enumerates the exact isadd/canonical-child association, owner cases and input-base bank occupancy; MODEL.json pins source/primitive hashes. Enumeration PASS:79 real adds/tree,78 stored non-root internal values,39 LEFT/39 RIGHT,40 leaf/leaf issues and39 internal/internal issues,399 conflict-free owner cases/tree. Both source causal association/leaf variants are included as static address-model cases, not a new runtime test campaign.

## Storage and ports

Primitive physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1 is a true one-clock 1R1W32x64 macro,5-bit addresses,64 active-high per-bit write enables. Its actual RTL registers rd_out on posedge clk; reads execute before writes in the same always block, hence same-address read/write returns OLD64-bit word. Silicon contents need no reset/init: metadata validity prevents premature reads.

| Profile | Leaf bank organization | Internal banks | Macros |
|---|---|---|---|
| ENG,three trees |15=(P3,residue5),48possible32b values/bank,24packed64b rows |11732b values per semantic role;59rows total/role across2macros |19 |
| NORM,one tree |15=(P3,residue5),16possible32b values/bank,8packed rows |3932b values per role;20rows/role,one macro |17 |
| XFIN |4ENG+1NORM |13trees |93 |

Two32-bit values share each64-bit word. One write activates exactly its selected32-bit half through the real bit mask; no read/modify/write port is required. A bank's read returns64 bits and the captured half selector chooses its32-bit operand. Leaf logical slot = tree*16 + floor(IX/5); bank=(arrival port,IX%5), row=slot>>1, half=slot&1. Each port's five consecutive input indices have distinct residues; all three ports can therefore make15leaf writes concurrently. NORM accepts every original8-bit base, including nonaligned/partially in-range flits: compute widened9-bit base+k and ignore IX>=80, with no8-bit wrap. ENG preserves its original base%5==0 and tree<3 acceptance conditions.

Internal node storage is coloured by its actual nearest semantic ADD consumer operand LEFT/RIGHT after pass aliases. Raw node parity is wrong (raw child3 aliases node12, consumed as rootRIGHT). Each non-root add result has exactly one consumer. Per-role slots are sorted static rank(node)+39*tree; macro=slot>>6, row=(slot&63)>>1, half=slot&1. The single shared adder writes at most one internal bank/cycle, independent of all15leaf banks. Root1 is not stored in SRAM: retain the existing direct wr_d root-result capture. A single issued node reads two distinct banks: leaf residues differ for adjacent pairs; internal operands have distinct semantic roles. There is no arbitration, read stall, flow control or imposed arrival ordering.

## Exact leaf payload and metadata semantics

Keep existing VD,iss,priority,duplicate/fault and go metadata semantics. Add two owner bits per live leaf (1040leaves across13trees ->2080FF); owner payload is unreset, qualified by existing validity. A current leaf hit chooses a participating input port. To preserve original bitwise-OR mv semantics even on faulted simultaneous duplicates, every participating port bank writes the OR of ALL current eligible input slots targeting that same tree/IX. Every port still writes only its own one bank per residue. Later duplicates replace the leaf value with that cycle's OR, matching the original overwrite rather than accumulating historical values. The encoded owner is captured from that same hit. Read selectors capture the OLD owner before any same-edge update, and macro read-before-write preserves original old-value reads. No validity/owner SRAM read is introduced.

All issue selection stays the original registered two-level lowest-index priority with stale-pick remasking. No claim that a different association/priority is acceptable. The EASSOC causal build derives its colour/rank tables from its actual ca/cb bindings, swapping roles for nodes9/10 and preserving a legal two-bank read while computing the intentionally wrong association. The LEAF causal build aliases logical leaf1 payload/owner to leaf2 while retaining original IXM validity/duplicate semantics; it does not add a second write to a residue bank on arbitrary nonaligned NORM flits.

## Read edge substitution and age boundary

At issue edgeE, original RTL captures selected V operands into a_q/b_q and fire/tag into f_q/t_q. The SRAM version presents addresses before the SAME edgeE, macro rd_out registers the selected old words atE, and bank/half selectors register atE. Replace a_q/b_q payload FFs with the post-SRAM response mux, retain f_q/t_q unchanged. The adder consumes both versions atE+1. On bubbles, registered bank selectors/f_q force operands0, matching the original empty one-hot OR mux, rather than leaking held macro data.

Proposed added payload/read ages are0, conditional on the existing exact proof. First output dates and calendar rates remain UNCLAIMED until those proofs pass. Do not leave original operand FFs AFTER the SRAM (that would add an edge). Existing valid-readiness metadata still changes on the original write edge; both implementations cannot select a newly completed internal result until the same registered priority stages have seen VD, so no new bypass/stall is needed. Tag pipeline, result-write edge, root-result capture and xfin result arbitration remain unchanged.

Scalar NORM tail is untouched: original ot_dsrom_divc has LATENCY9; +eps uses LA6; original rsqrt has 1+3*(3*LM+LA)=64 at LM5/LA6. Preserve original multiplier LAT5 and all vector delays. The VS-only LAT6 multiplier is NOT a legal scalar substitution. No aggregate first-output age claim is inferred from comments or a nominal primitive latency.

## Concrete implementation boundary

New opt-in source rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv will provide NORM/ENG finish successors and a bounded selected-profile SRAM bank helper. Existing shared arithmetic files and legacy finish defaults remain unchanged. The xfin owner adds only an explicit OT_S81DV_XFIN_SRAM selection for the two finish instance types. Compile-time selected profile guards reject unsupported NV/K/P shapes. Preserve original pre-capture go_t/iv/ib/it/id and all ready/issue/fault trees; replace only persistent val payload and operand selection. Keep metadata in small FF structures; no heap payload flop fallback.

Mask/control fanout must be real: byte-local kept write-mask predicates (no shared half-enable driving64pins), per-bank addresses/enables, bounded metadata/control regions, and an identical TWO-edge reset forest with enough regional leaves (prefix fanout<=24, each leaf<=24controlresetloads). Owner bits and all SRAM payload are unreset. Preserve original reset release age; no storage or fanout waiver. Final native mapped census must cover macro pins and all reset/control roots before physical admission.

Existing qualification only: tools/s81_dv/norm16_bench.sh base/mutbase/mutleaf xfin; tools/s81_dv/xfin_eng_bench.sh base/mutetag/muteassoc with the existing arbitrary arrival order/gaps and golden files. Compare exact output dates as well as association/golden data before confirming proposed0age delta. Required exact source-mapped native census follows mechanism proof. No new broad campaign or physical run until source/native prerequisites pass.

LEF31.968x17.280 yields552.40704um2 each,93macros total51373.85472um2=0.05137385472mm2 MACRO AREA. Physical capacity190464bits holds65728logical persistent payload bits plus existing416root-result bits outside the arrays. This is not a floorplan/die-fit/PG/clock/route area claim; future93-macro placement must supply actual channels and physical proof.
