# QC native reset receive placement fix

Image: `results/qc_import_0824/reset_reach_fix.png` (personally viewed).

Verdict: PASS-COND for fresh-source preparation/import; P&R remains held until actual full reach and all required PG/clock gates pass.

The actual native `sl_E0_fw/rst_o_0` driver reaches two first reset receive flops at 483.618 and 469.233 um. The old preflight checked only the b0/root centroid and missed these direct native fanout endpoints. Move only those two first receive flops down 79.92 um, an exact R0-row multiple. The image shows both reset wires shorten to below 405 um; the added local clock branch is about 80 um, and each first-to-second reset relay remains below 85 um. All other cells, RTL, clock/reset graph and latency cycles stay unchanged. Two explicit type-union body windows replace opacity at the new homes; their static census is 0 core intersections/0 outside partitions. Full fresh actual-ODB preflight and complete pin-to-pin reach must confirm the placement. The original FAIL is retained.

GEOM-57 conditions from the inherited import still apply: routed slew/arrival for the 462-um clock wall, routed edge polarity on the 921 A taps, and real PG/local FF clock connections. The picture does not establish route/timing/IR or die freeze.
