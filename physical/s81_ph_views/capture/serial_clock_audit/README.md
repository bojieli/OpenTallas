S81 capture serial-clock audit, 2026-10-13

The CLOSED dsfd_capt_x_m5 route omitted ckv from create_clock and treated it as data. Its ETM ckv pin has no clock attribute or serial timing arcs. This read-only measurement adds a 1111.111 ps clock on ckv[0] in an isolated STA session, propagates actual routed SPEF, and reports SS/TT/FF sink arrivals. It does not change the closed route or weaken timing constraints.

TT boundary mean 670.7 ps, min 76.9 ps, max 1371.1 ps, spread 1294.2 ps; 8671 serial-clock sinks. The current capture parent cannot claim clock closure with this view. Structural repair must supply real serial CTS and timing arcs.
