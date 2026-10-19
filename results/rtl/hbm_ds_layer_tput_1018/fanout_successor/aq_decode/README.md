# AQ structural decode successor

Frozen RTL `9d7897923`, baseline `3eea95a41`. No public port changes, SRAM changes, or added clock edges. Modeled retained-state cost is +107 FF at queue depth32, +115 FF at production depth64; actual mapped area and clock resources remain admission requirements.

The canonical next-state datapath feeds retained local head/count state. Independent head prefetch identity and occupancy domains separate row/read capture from bank/column capture. ACT word and timer controls have distinct registered owners. Refresh reservation and row-command bank identity use encoded registered bank plus valid, decoded locally after the original capture edge. Bank timer decrements saturate in the arithmetic datapath.

Both actual Verilator5.050 proofs compare all externally visible outputs and held-bank debug bits against the original18bd AQ, including repeated occupied resets. Each runs23,968 checked edges. Depth32:2238 pushes/1982 columns/1677 row commands; production64:2385/1873/1258. HEAD, ACT and REFRESH source mutants fail the required mismatch check at both depths. Receipts explicitly pin queue depth and input file hashes.

Qualification remains OPEN. Earlier4cd actual mapping had112 roots over32 loads (71 nonreset); bb56 had117/76. Those failures are retained and do not qualify this successor. Parent BW owns frozen9d789 mapped census in ep8 `hbm-bw-aqmap5-1019`, then combined CFG/ring integration and the full66-operation/154-GO production replay. `mapped_state_contract.json` and `bw_aq_state_audit.py` require actual kept bit counts, D/clock/reset pins, and netlist-bound load evidence. No CTS/route or performance adoption is authorized by component proof alone.


## Byte-partitioned regional successor

Final AQ RTL is `a2cb44a57`, component evidence in `proof_a2cb_wq64_regions8`. It adds optional `ROW_REGIONS` (default0, enabled8) and producer-owned `wr_row_regions[151:0]` for local look-row writes. Scalar row input retains canonical head/queue/fresh captures. Parent BW owns64 real producer selector FF and152 internal wires; those are additional to AQ cost. No external hardened-wrapper port or added edge is claimed.

Actual9d789 mapped-copy audit passes the expected kept-state counts and D/clock/reset classes, but142 total/101 nonreset drivers over32 remain a physical rejection. The successor partitions19-bit row captures into <=8-bit registered owners, adds independent per-word bank counts/head bank identities, and partitions head capture and tail-set state. Cost relative3ee: +625 FF at productionQD64, +549 at diagnostic32, zero added cycles or SRAM ports. Bank resets gain14 sinks each and need actual parent reset-tree rebalance. Source assertions cannot qualify loads; a combined actual mapped census, full66op/154GO replay, native timing and physical admission remain required.

ProductionQD128 was rejected and reverted by parent (6659b35b0); QD64 is the agreed production/physical binding.

Latest `a2cb44a57` default32/ROW_REGIONS0 also passes the original23,968 checked edges and2238/1982/1677 event counts plus all3 source mutants; see `proof_a2cb_wq32_legacy0`. All helper proof jobs ended normally. Parent BW owns the combined physical/mapped and66op154GO production follow-through.
