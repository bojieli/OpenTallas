# Independent P3 shared merge safe reset variant

Baseline SRAM gate1003344 continues as evidence in its original tree. Its mapped netlist retains16 separate adder reset flops, each driving432 RESETN pins; rst_e drives454. These copies were NOT merged, and they do not satisfy the32-load target.

This independent kit enables OT_FP_DATA_NORST: the existing adder DRST0 implementation resets valid bits only. The adder already qualifies fault by valid_out; consumers use the fixed valid return schedule. Stale data and err during invalid cycles are unobserved. OT_HNX_ATT_SAFE_RESET additionally creates explicit kept ot_rst_split vector families:32 copies of the wrapper rq edge,16copies of each existing smerge control reset edge and16copies at each adder's existing rst_m edge. All copies have identical D/clock and no additional edge or latency. The main reset_relay_split pass proves identical flops and distributes consumers with max_loads32; TSV plus mapped RESETN counts must independently confirm the bound before item3 PASS. No manual waiver.

Data latency, reset-release latency, protocol and II stay unchanged. The source bench has explicit HNX_ATT_SAFE_RESET=1 selection, records safe_reset=true and isolates its Verilator binary directory. Both defines are opt-in, off by default.

Same432square frame/18 padded SRAM macros and central arithmetic band as baseline. Prior standard-cell area11,277um2 is conservative input until this variant's gate synthesis measures the valid-only implementation. Clock spread/timing/placement and data pin wire lengths await gate. Existing safety packet applies except item3 is FIXED structurally / awaiting measured max-load witness. Reset raw input drives32 wrapper copies, then each replica distributes only local registered reset consumers. Data cycles and compiler schedule charge0; provisional die-outline charge remains+69.215mm2 before real DIE refit.

Full25-leg exact matrix with safe reset defines running on fleet/Verilator5.050. Critical gate/review only; NO REVIEW.json or submit. Helpers tools/ref_tile, closure_loop and common_flow reset splitting are origin/main overlays and must not be committed as lane changes.

Mapped reset proof collected from gate snapshot0fdd5047a9353e55fb90de1986012353468cc4ad9bea720688a4885191bdff59: every named reset family has at most29 mapped input loads. Worst rst_ev29, wrapper rqv10, each adder rst_mv7. reset_proof/hnx_safe_reset_native.json pins the full mapped netlist SHA256 and counts. The splitter redistributed rqv/control families; its REFUSED rows for unnecessary adder copy bits are nonbinding because the complete per-adder input load is already7 and the mapped count independently meets32. No progressing snapshot was edited. Reset portion of item3 PASS; remaining generic netlist fanout/timing still evaluated by the gate.

First safe exactness batch: shared slice160/160 PASS including per-lane runs and cross-SM equality, publication576/576 nodes PASS; storage skew6 and publication5 mutants FAIL with committed witnesses. Full25 matrix remains live. Data/reset latency and measured spans unchanged.

Current signoff policy from coordinator HANDOFF section2 is TT setup plus FF hold/die TTFF>=0; SS is sensitivity. No headline closure is claimed before gate verdict.
