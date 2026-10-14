# Actual SM OWN / real ICG gating diagnostic

The real three-corner static model fails setup. Exact parent associations and clock-entry accounting pass for all 144 ENA checks. This is an optimistic isolated timing diagnostic, not physical/native pause or epoch qualification.

| Corner | Minimum setup (ps) | Minimum hold (ps) | Negative setup / 24 |
|---|---:|---:|---:|
| TT | -128.970535 | 348.432587 | 8 |
| FF | 43.859653 | 241.497437 | 0 |
| SS | -425.149872 | 553.868713 | 24 |

TT fails both ENA polarities on XS (two mappings), PT_E and PT_W. SS fails both polarities on every child. Real negative Liberty hold constraints are preserved; all measured hold checks pass.

`receipt.json` includes each indexed check, input hashes, accounting residuals, and limits. The exact helper SHA is recorded in `manifest.json`; reusable generation code is `../probe_sm_own_gating.py`. `frozen_inputs.tar.gz` preserves all seven exact published macro views and the three real SEQ libraries. Frozen image identity, actual executed Tcl/SDC, source-anchor SDCs, and terminal ot-run logs are included. Historical `plan.json` remains an immutable PLAN_ONLY document; execution status is in `receipt.json`.

Each ICG CLK is the actual assigned child's RAW source; ENA is OWN registered cut_8870, SE=0, and GCLK feeds that child's actual clock pin. All clocks are related 833.333 ps. OWN source latency is -Rown. At zero RAW latency, gate and ideal-entry insertion are measured at actual child clock capacitance; RAW then receives -(gate insertion + Rchild). This proves accounting for the fixed exported child model. Setup uncertainty is 150 ps or 210 ps when either TT total clock reference exceeds 300 ps; hold is 100 ps. There are no path exceptions. GCLK source slew is never overridden.

For TT PT_W falling ENA, OWN raw clock-to-output is 380.280884 ps and Rown=149.2 ps, giving arrival 231.080887 ps. RAW next edge is 833.333-(429+52.432831)=351.900177 ps; subtracting setup uncertainty210 and actual ICG setup39.789806 gives required102.110359 ps and slack-128.970535 ps. Ordinary data reach is not a substitute for this early RAW gate edge.

Pulse-width coverage remains OPEN. Real conditional CLK pulse-width groups are retained in the libraries. `report_check_types -min_pulse_width -verbose` emitted no checks even in separate stable ENA=0 and ENA=1 cases. Restoring unknown ENA reproduces all 48 original checks in each corner. Exact reporter API dispatch is retained in `pulse_api.receipt.log`. TT `report_edges` verifies imported/evaluated real width arcs: !ENA*!SE falling-to-rising20.14 ps; ENA+(!ENA*SE) rising-to-falling6.10 ps and falling-to-rising23.41 ps. Nominal RAW high/low waveform is416.6665 ps, but this observation is not a conditional pulse-width check PASS.

The source0 ps anchor matches actual source SDCs but extrapolates below the ICG characterized5 ps minimum. Real delivered GCLK slew is nonzero (TT95–166 ps), while child R comes from the original zero-slew insertion anchor. Conditional child R at observed GCLK slew remains uncalibrated. ENA/entry wires are ideal, normal unused DATA/reset pins are tied only for this isolated arc fixture, and no functional/source/physical ingress qualification follows. OWN cut_7768 self-related output-clock arcs remain untouched and unused. Initial no-technology failure and unsampled-graph property crash are retained; terminal successful scripts initialize technology and sample timing before clock properties. No executable negative mutant coverage is claimed for this receipt.
