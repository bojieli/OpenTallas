# Release HBM SU/BW pickup, 2026-10-19 12:41 PT

Evidence only; no new simulation, synthesis or route launched. Existing jobs preserved.

| Vehicle | Actual status | Qualification / next step |
| --- | --- | --- |
| BW n64 full96 | Previously committed PASS 66 operations / 154 GO, END45260 | Functional evidence only; strict-rate failure retained. |
| BW n64 11:37 | Terminal macro placement inventory failure | Immutable failure log retained; corrected existing 11:41 run is independent. |
| BW n64 11:41 ep8 | GRT setup repair live | Placement-RC TT macro->register -189.64 ps, FF hold +35.695 ps; pin-only TT spread 60 ps / FF64, but all-pin TT80 / FF84 ps. No pass or submit. 23 emitted macro blocks vs kit model27 needs exact inventory reconciliation. |
| k9s2 ep4 | Global placement live | Known reset6245 and old source depth remain blockers; old threshold WARN cannot authorize bind. |
| k9r ep4 | Canonical synthesis live | 26 reset-copy families coarse table OK, max32; full mapped BUF/INV-transparent all-driver census still owed. Source helper must be merged/synced before any submit. |
| GQ k1 ep8 | CTS hold repair live | Current hold -88.651 ps, AQ1 s0_x479; not terminal. |
| GQ k2 ep8 | CTS hold repair live | Current hold +21.668 ps; native spread and final gate still owed. |
| cxijq1019s | Gate WARN, auto-submit REFUSED REVIEW_REQUIRED | Commit08f64ff5f; prior reset86 / data33 means current SAFE32 proof absent. Root PNG/checklist review needed only after structural/source blockers resolved. No submit. |
| pretree p3 | Timing CLOSED; daemon collect live | Final routed reSTA TT+93.20 / FF+18.72 / DRC0, SS sensitivity-233.51; ECO36603 cells. Reset340 and transparent all-driver census, routed native parent match remain adoption blockers. Do not mark task complete from timing alone. |
| PVM s1 | Submit REFUSED BENCH-LINT | Missing committed positive/mutant witnesses; previously rejected SRAM geometry/reset285 remain blockers. No blind regate, submit or bind. s3 is owned by separate active lane. |

Exact pickup paths and process identities remain in pending_results.txt. This packet records snapshots, not release qualification. No SU/MU token claim follows from these component results.
