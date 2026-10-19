Actual startup dependency proof follow-up; first-valid lifetime join UNPROVED

This read-only extraction uses the frozen native_final ODB and all actual cell/net names, with only BUF/INV/HB collapsed with polarity. Unlike the congruence receipt, no copy alias replaces an input driver in the extracted equations. Copy aliases are used only to verify intended source identity. There is no timing rerun or ODB mutation.

For each copied FF and its ultimate original FF, compare actual source/input expressions recursively. Equal actual signals require no state assumption. Distinct same-source/master combinational cells require equal corresponding inputs; distinct actual FF pairs introduce a one-clock-edge dependency. Acyclic dependencies establish convergence under arbitrary original/copy initial states after a finite number of same legal clock edges, provided actual native data/control timing is met. Every FF pin, including reset/set/clock, participates. No clock enable, reset value or zero-init assumption breaks a dependency.

All1155 FF pairs have finite bounds:626after1,402after2,127after3edges. For the732 unreset copies:608after1,92after2,32after3. All32three-edge unreset copies are RXcalendar seg1. The wrong-source/self-feedback mutant changes one actual copy D input and fails the finite-bound checker (49dependent copies unresolved, explicit leaf/polarity mismatch); it cannot silently pass by alias equality.

This proves replica-to-source convergence, not source-to-golden initialization or defined observable state. Early unequal copies could affect original state or pre-initialized storage before convergence. No claim that valid outputs or configuration writes are suppressed in that interval follows from this graph alone. The existing snapshot is source b30f8454c6db1309ee4ec7a154943f6c737b43f2; production producer/reset source has not yet been joined to this proof.

Source findings to join, not assumed guarantees:

- rtl/lib/ot_rst_pipe.sv documents running clocks during reset, assertion reaches regional reset afterSTAGES2 edges, release after2+STAGES=4edges. A source-bound minimum external assertion duration and observable qualification are still needed; no additional boot cycle is authorized by this receipt.
- ot_qwen_d2d_cal_seq.sv programs all32TX+32RX words and both segment bases before cal_ready; normal start requires the image/configuration to settle. Calendar seg1/table storage is not reset. The actual parent producer/reset/wiring/image must prove each used word and base is defined before start. The physical top's cfg/start inputs are external; the sequencer is not instantiated in this gate.
- Existing testbench reset repeat4 cannot establish a production minimum pulse. Abort/restart must preserve established correspondence or reestablish it before valid use, including actual legal phase and asynchronous reset timing. These joins remain open.

Reproduce the read-only graph proof locally with Python/Tkinter:

    python3 analyze_startup_copy_pairs.py
    python3 analyze_startup_copy_pairs.py control16_startup_feedback_mutant.tsv

Both commands emit diagnostic receipts. Inspect pair_dependency_result (PASS for real, FAIL for mutant); top-level verdict stays DIAGNOSTIC_ONLY until first-qualified-write/first-valid observability, reset/abort/restart and actual native source contracts are proved. The previous no-gate/adoption=false decision remains binding; dense SRAM routed access remains independently unqualified.
