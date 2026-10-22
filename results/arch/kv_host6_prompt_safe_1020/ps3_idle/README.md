# PS3 idle semantic prototype

The inherited idle expression required !m_rready && !m_bready while both are permanently one. PS3 replaces it with registered quiescence over contexts, outstanding steps, FSMs, event queue, pending SQ, actual command/response valids and slave responses. Readiness is not activity. The host leaf also observes all ten pin stations through a private qkd_host_pin_channel_ps3 busy port; the root observes physical CSR-side valids before the demux pipeline. No shared/default source changed.

V5.050 actual full host/control/pin hierarchy passes four users, eighteen steps, twelve CQ entries, max four outstanding, exact per-user outputs and no faults. Idle is reachable after reset and after all contexts complete. Real partial AW before W checks the first boundary edge; real held read/write responses, paused allocated contexts after engine drain, and a rejected descriptor with a deliberately full CQ independently check each busy category. The error event holds while no context, DMA or step is active, then drains after CQ space returns.

All four causal mutants fail with committed logs. The earlier stable-response-only boundary mutant survived and prompted the first-edge test; its earlier result is not qualification. The initial root first-edge test also failed before the separate root observer was added. Current logs correspond to v5 bench/source.

Model: no added functional datapath cycles, two extra registered idle observations (three total); one edge to observe root-side activity. Fixed bench measures nine edges from held response release to idle, eight from final CQ write to idle, including existing pin-station handshakes. These are exact fixture measurements, not a universal backpressure bound. Selected source ties all clocks; no generic multiclock claim.

This is SOURCE/SEMANTIC ONLY. The distinct PS2 native primitive source has an independently reproduced first-edge SRAM corruption failure. PS3 has not been mapped, copied, cold-qualified, routed, or adopted; no qualification transfers from PS2. The private raw-por memory-access inhibit prototype is a separate new reset contract awaiting ROOT review.
