# P3 shared attention merge: SRAM recovery

The P4 evidence gate continues FF hold repair after four hours, with >27,000 inserted buffers on 8-stage data shift registers. Safe-design item5 forbids those delay chains. This branch replaces36,864 shifting data bits with stationary SRAM and the184-bit return metadata pipeline with an addressed circular table.

The18 hard128x256 macros use73,735.14um2 of reserved footprint; only36,864 of589,824 installed bits are used. Each logical512-bit lane/level bank has paired256-bit halves. Read ph+1 and write ph on each edge, so SRAM registered reads preserve the original eight-edge recurrence. The same-residue read and write are separated. There are no additional data cycles or II changes.

The hnx SRAM alias reserves2.16um of whitespace above the original41.04um macro. Its43.2um footprint permits N/S bare-face abutment at43.2um origins. All pin positions, HDL and timing tables are identical after renaming; the checked normalization proof is evidence/padded_macro_identity.json. Pinned source macros are unchanged.

Measured standard-cell area11,277.25092um2 vs23,587.26156um2 before conversion. Draft432x432um outline =0.186624mm2/column,95.5515mm2 per512-column die. Against the prior226.8square planning slot, this is+69.2152mm2/die: f4c_t9p3~836.63mm2 before any die reshaping/channel change. This is a physical planning charge, not a measured new die.

Evidence: 64x512 pilot publication576nodes bit-exact and mutants1..5 FAIL; storage-address-skew mutant6 FAIL. Paired128x256 slice matrix running; completed nominal NL3/NL4 runs match pre-conversion timing and goldens. Padded macro publication576nodes PASS. Verilator5.050. Matrix results will be collected without replacing prior evidence.

Safe-design checklist before gate:
1. PASS: existing RTL registers all data pins; reset uses wrapper rq plus kept rst_c/rst_e/rst_m stages. No added functional latency.
2. PASS by floorplan intent: central arithmetic fence and split north/south macro banks; macro-to-core straight-line bounds below405um. Pin-to-landing wires use the existing extra landing register and face placement. Gate must confirm placement/timing.
3. PASS structurally: existing kept one-hot selects per32-bit adder and per-adder reset copies retained. Gate netlist checks remain required.
4. PASS structurally: registered operand selects and landed decode from step4 retained; the former SS sensitivity setup was-58.8ps at770ps; no deeper combinational cone introduced. Clock gate measures actual paths.
5. FIXED: bulk data in18 SRAM macros;184-bit addressed metadata ring. No bulk shift storage.
6. PASS geometry: all18 origins on43.2um lattice; bare N/S padded abutment; W/E channels34.776um; one central full-width channel contains the324x64.8um arithmetic fence (~54% standard-cell density before wrapper pin flops). Full-face N/S data pins under6/um; square outline. Generator findings have only46% total-fill WARN. Macro constant mask/repair pins are tied as in the existing closed macros.
7. PASS plan: E clock faces central register mass, reset staged, io_hold_margin0.03ns. TT/FF insertion and <=80ps spread await CTS.
8. PASS: static event schedule, unchanged eight-edge bank recurrence, no credits/backpressure; zero data cycles added. Die area charge above must reach DIE/CMTP before binding.

Critical tile: report PNG/checklist only. No REVIEW.json or submission. Draft hold_merge stays true until coordinator review. No programme merge until exactness is collected.
