# SC actual three-buffer geometry review

Personally viewed auto_geom.png and actual_tail.png from the completed native import, EPYC2 unit1067116-1793613522. Exact saved dump: /srv/opentallas-scratch2/claude/codex-qc-sc-red-1101/sc_buffer_geometry/sc_buffer_geometry.tsv; honest SC_DATA_GEOMETRY_CHECKPOINT.odb is retained. Three existing BUFx6f repeaters follow the reviewed monotonic path. Actual pin-to-pin hops are112.4965,112.091,111.983,111.824 um; each edge fanout1. All other instances, FFs, masters, poses/status/DNT, pins, source and full CLOCK/DATA graph guards pass. Native body check and PG751910/open0 pass.

Full actual metrics: r2r404.92 um/zero above405, pinp90/max11.3/41.44 um,42665 rooted sinks, own-leaf32 um. Raw column1.091/aspect2.102/GRTNA are preserved; prior same-placement GRT0 capacity evidence does not transfer across these three moves. Original actual TT−411.17 from the collapsed444.69 um first hop remains failed until measured. This is the dn_i[47] valid-control capture, despite the shared_rst instance name.

PASS-COND for ROOT's standing ONE fresh same-deck full CLOCK+SIGNAL GRT50 plus TT/FF replay. No GPL, resize, CTS, DRT, new cells, source edits, or predicted timing PASS. Require fresh overflow/coverage/PG and matched timing. Owner was notified to proceed within the standing scope; no duplicate job or STA by this reviewer.
