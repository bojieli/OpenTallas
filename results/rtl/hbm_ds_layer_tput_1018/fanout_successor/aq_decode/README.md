# AQ structural decode successor

Frozen RTL `9d7897923`, baseline `3eea95a41`. No public port changes, SRAM changes, or added clock edges. Modeled retained-state cost is +107 FF at queue depth32, +115 FF at production depth64; actual mapped area and clock resources remain admission requirements.

The canonical next-state datapath feeds retained local head/count state. Independent head prefetch identity and occupancy domains separate row/read capture from bank/column capture. ACT word and timer controls have distinct registered owners. Refresh reservation and row-command bank identity use encoded registered bank plus valid, decoded locally after the original capture edge. Bank timer decrements saturate in the arithmetic datapath.

Both actual Verilator5.050 proofs compare all externally visible outputs and held-bank debug bits against the original18bd AQ, including repeated occupied resets. Each runs23,968 checked edges. Depth32:2238 pushes/1982 columns/1677 row commands; production64:2385/1873/1258. HEAD, ACT and REFRESH source mutants fail the required mismatch check at both depths. Receipts explicitly pin queue depth and input file hashes.

Qualification remains OPEN. Earlier4cd actual mapping had112 roots over32 loads (71 nonreset); bb56 had117/76. Those failures are retained and do not qualify this successor. Parent BW owns frozen9d789 mapped census in ep8 `hbm-bw-aqmap5-1019`, then combined CFG/ring integration and the full66-operation/154-GO production replay. `mapped_state_contract.json` and `bw_aq_state_audit.py` require actual kept bit counts, D/clock/reset pins, and netlist-bound load evidence. No CTS/route or performance adoption is authorized by component proof alone.
