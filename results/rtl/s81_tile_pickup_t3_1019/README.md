# S81 tile result pickup, 2026-10-19 17:34–17:48 PT

Source-pinned existing jobs only; no source mutation, rerun, cancellation, submission or adoption in this packet. Actual final wrapper receipts are preserved beside their source specs, PNGs and bounded native log files. Viewed s10c floorplan personally: four fixed macros, original full-face pins, one mid-east clock entry.

| Run | Actual result | Closure implication |
|---|---|---|
| SHLK s10c / 7e92217f5 / archive0e02ab9a… | wrapper WARN; GRT overflow0; boundary TT/FF76.1/66.2ps | **REFUSE adoption:** actual TT setup−40.65ps / FFhold+30.01ps in GRT; placement+45.694/+20.585ps does not transfer. |
| C199rq / b4648a6e2 | wrapper WARN; boundary22.6/20.0ps | Legacy known1060 fanout remains unsafe; no full native/PG closure. |
| C199rr / 94b17b213 | wrapper FAIL CTS137 | Actual cts.log GATE_STALL14400s, 38,360 hold iterations, WNS−79.690ps/TNS−3126.349ps. Not an OOM claim. |
| LEP A/H b64 / bb66563eb | both wrapper FAIL GPL-0305 | Real global-placement numerical divergence; no CTS/placed occupancy. A/H artificial routability area+179.32/+164.20%, final placed-model area22,834.50/24,141.94um². |

SHLK grt.log explicitly reads native TT and FF cell/macro Liberty. The mode name SS is not SS sensitivity. Native textbook threshold only reports >=256; the actual report still contains OR3/OR2/NAND2 combinational outputs with597/586/584/583 and four558 loads. Source README explicitly leaves those trees unresolved and waives old reach351pairs/max519um; those exceptions do not satisfy current <=32 transparent-terminal fanout or <=405um requirements. Four old16x257/289 macro views also have local .096um contacts; averaging external face pins does not qualify them. Source archive, immutable source manifest, all consumed helper hashes and native image identity are retained in gate_result.json; the current SDC reorder helper is e4debd987a in that archive.

LEP source wrapper temporarily replaces full physical core with a narrow64.8um row-band core while all20 fixed SRAM macros remain outside. Logs confirm this geometry contract during GPL, then restore physical core after failure. This is a concrete structural optimizer-geometry incompatibility; increasing inflation/tweaking density is not a closure. A genuine RX/TX hardened decomposition is assigned separately, preserving all failure evidence.

Existing TOPK succ2/succ2c and XGR/XGR2 jobs remain progressing; no terminal local receipt at pickup. They are not re-launched. SHLK successor work is separate: real default-off source enable replication and truthful p192 dual-clock masters, then bounded hardened SD child. No SOURCE, timing, PG, route, token or release PASS follows these wrapper WARNs.
