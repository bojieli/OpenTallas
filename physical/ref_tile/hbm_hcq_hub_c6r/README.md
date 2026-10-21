# C6r quarter hub: exact programme SRAM clock binding

Source unchanged from C5r e6c44aa64; params DRLY2/CHX11/SAFE2, default GATHER_PHASE23. This is not an alias for selected die GATHER_PHASE39. Actual C5r mapped programme SRAM u_q.g_qcal.programme.u_program uses clk; C5r omitted the strict raw-memory binding, so CTS stopped before measuring any tree. C6r uses the existing official generator contract with actual TT/FF Liberty validation. No shared helper, RTL, clock phase, port, data edge, compute inventory or geometry change. Cause/model receipt: results/arch/hbm_c5_clock_binding_1340_1021/MODEL_AND_CAUSE.json.

SAFE eight points before physical gate:
1. Pins: retain every source-registered port and the exact four full-face pin assignments; no new landing or added stage.
2. Reach: retain 734.4 square pin-bound parent, all four hard-tree placements and original macro channels. Actual gate/route decides timing; old soft reach diagnostic0.6um is not a route qualification.
3. Native fanout: exact old mapped body max32 PASS; new gate must measure its own actual source, no native waiver.
4. Depth: old mapped521.8ps depth disclosed, actual parent boundary and routed timing still required.
5. Storage: one actual1024x256 programme SRAM plus four closed tree children; all actual macro clocks remain timed, no blackboxes or invented Liberty.
6. Floorplan: actual734.4 square, old measured std8052um2/macro62706um2, fill13.3%; continuous central band/pin-bound perimeter retained. No density squeeze; exact PNG review required before submission.
7. Clock: clk remains controller CTS plus its actual SRAM clk. Four exclusive clk_t ports preserve hard-tree references TT186.6/194.5/199.6 and FF152.7/160.9/166.5. Exact raw binding rejects wrong instance/master/pin/root. Pin/child-boundary<=80TT/FF and actual timing mandatory; no insertion-only failure or all-flop relabel.
8. Calendar/reset: old source reset/data/epoch schedule unchanged; zero added edges. GATHER_PHASE39 die successor needs actual coherent reader source/params and independent qualification, no default23 view alias.

C5s GPL-0305 divergence remains a separate actual failure; it is not retried unchanged. Existing behavioural positives/mutants are retained at exact original source, and submit uses normal guards after gate geometry review.
