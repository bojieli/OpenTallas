# VM glue regional gate projection

This is a private physical gate projection. Do not merge the whole branch to main. It starts at precursor 4c1c62af7 and copies the published f6acee183 clock, native and reviewed FIFO helpers. Main publication must preserve current shared helpers and select only the intended regional RTL, generator, kit and evidence paths.

The existing three-root RTL has zero added edges relative to g7. Its registered seam hops, finite storage, reset behavior and pin relay chains are unchanged. SW passed 37,520 comparisons and NW passed 33,768 comparisons over 4,000 cycles. Disabling either regional clock fails each quadrant. Actual source and fleet receipts are in bench/summary.json.

The outline stays 648 by 1555.2 micrometers. Boundaries at 580.1 and 976.0 micrometers follow the measured lane groups. The new kit source derives each boundary port's domain from its actual first or last register clock. It retains the g7 relay lattice and adds geometric fences by actual pre-CTS clock net. All roots are related and all cross-region data paths remain timed. No clock, fanout, data path or hold rule is waived.

Canonical SW and NW generation passed on Gold2 unit 1650565-1792647018. Generated kits are committed at 989acb52f. The guarded CTS gates must pass the actual native census at maximum 32 and no role errors before physical layout. Final clock, timing, reach, layout review and die neighbor checks remain required. A functional pass or generated kit is not physical qualification.
