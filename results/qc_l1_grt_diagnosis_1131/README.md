Actual L1 retained-GRT diagnosis

The exact two unique setup endpoints are EXP nint[6]/D falling (-14.64ps) and HEAD s1_rows[221]/D rising (-0.67ps). Two emitted EXP records are identical. The original final FF/BC report also has a real RR hold violation (-2.52ps); the earlier +8.24 summary does not close that final check.

The diagnostic used the retained actual GRT estimator and exact final TT SDC/library selection, with no fallback or physical changes. Its worst TT path exactly matches the retained final native report. The FF path is retained original evidence, not a TT-session reconstruction. Summary-versus-final causality is deliberately not called a selection bug: later native reroute/posthook operations separate the timing points.

All CLOCK/SIGNAL nets have DB guides, and all1936 CLOCK nets have native guides with original flags intact. The683 missing external SIGNAL guide names are a separate late-export defect already owned by KIT. Neither coverage nor the earlier MM summary is substituted for final timing.

This packet requests review of the actual state join before proposing a smallest DATA fix. No ECO, additional route, placement, resynthesis, proof or DRT was run. Original files and failed timing remain intact.
