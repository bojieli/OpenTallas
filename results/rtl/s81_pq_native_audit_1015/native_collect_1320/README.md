# Terminal collective boundary audit, 2026-10-15 13:2x PT

These immutable source-bound component receipts audit the exported TT/FF Liberty and insertion.json from closure-record commits 3d2b44b64 and 4eb757d5e. They do not adopt source, overwrite previous evidence, qualify full native execution, or reroute a closed component.

| Candidate | TT setup / FF hold / DRC | Launch | Capture | Spread | Boundary result |
| --- | --- | --- | --- | --- | --- |
| Calendar7 c2n | +9.78 / +3.12 ps / 0 | 185.17989 ps | 226.60958 ps, rst_n | 43.0 ps | FAIL |
| VM boundary b7 | +88.15 / +16.88 ps / 0 | 181.08936 ps | 173.72547 ps | 58.3 ps | PASS |

Calendar failure is restricted to the common rst_n pin entering three output roots: capture 225.97495, 223.9134, 226.60958 ps at clk_outputs[0:2]. Its worst ordinary data capture is c_cmd[43], 165.81666 ps. The source already contains one ot_rst_relay per root. A structural successor should bring the reset landing flops to the assigned pin or expose independently placed per-root reset entries; preserve normal static-calendar edges and verify reset sequencing. Do not assume inserting another logical relay alone fixes placement. Inspect actual routed pin-to-reset-landing paths before choosing physical changes.

The raw audit treats every Liberty arc with its own related clock. Generic pin_metrics aggregates multi-clock input arcs and then uses the first clock when calculating q_lb/p_lb; that overstates this calendar reset capture as 234.47495 ps. The clock-exact result still fails the unchanged 190 ps limit. This receipt does not modify that shared tool.

Source identity matters: calendar7 is absent from the audit base origin/main, and VM boundary main lacks the candidate PINCAP parameter/reset relay. Thus VM b7 is a passing candidate view requiring source integration and compiler/composition proof, rather than evidence that the current main module is physically qualified. Its ETM also has 563 input bits without timing arcs (plus excluded VDD/VSS), consistent with parameter/logic optimization but requiring source-bound integration classification. No unconstrained-input waiver is inferred.

`collect.py` regenerates these JSON records from immutable extracted artifacts and the original closure-loop job JSON. Its parser is the committed pinreg_audit.py. Values are compared at raw precision. Exported insertion measurements themselves are limited to the precision recorded in insertion.json. No heavy jobs were launched; all operations were read-only parsing of terminal evidence. Existing positive/mutant jobs remain the original provenance, not newly repeated tests.
