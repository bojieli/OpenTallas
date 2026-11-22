# QC Glue A5 i1t record timing geometry

The inherited E9 A5 i1t route reached DRC 0 and had no antenna violations. Its PRD result records route, clock check, and finish-post success. The pass has no post runner, so official TT and FF signoff has not run. The legacy stage 6 report still read a SPEF with 1,001 forwarded-clock duplicate-name warnings.

The routed ORFS setup path from `u_bound.u_sys_face.rx_payload__ot_q[512]` to `u_bound.u_sys_face.u_ot_pr_core.u_record.u_333/Q` is −77.67 ps. Launch at t23 arrives at 240.26 ps. Capture at t46 arrives at 182.81 ps within its cycle. Data delay after launch is 851.43 ps. The viewed cell-order plot from the actual final DEF traces 703.46 µm in Manhattan distance, with a 119.286 µm longest leg. The early portion doubles back through the common payload inversion before reaching record logic.

E9 `fam-qc-cb-r2/nov22_glue_rx_rope/record_path.png`, `path.json`, and `record_precheck.patch` retain the evidence and private prototype. The prototype takes seven reserved-field reductions at the existing RX capture edge for the record receiver. The embedding receiver continues to see its original payload. The exact routed and preferred V3 N32 record modules have identical SHA256. SAT passed 2,067 arbitrary input and state bits across 3,139 output, next-D, and reset comparisons. Candidate wrapper and core parse. Physical proof remains pending.
