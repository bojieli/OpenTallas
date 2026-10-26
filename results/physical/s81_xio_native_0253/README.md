# XIO r1 CTS native diagnostics (not routed qualification)

The request r1 is rejected: native TT capture276.58174ps exceeds190ps, nine input pins over limit. Its E collective input crossed to W decode/output flops before capture. Corrected source643419d7d adds real input capture, request+2core and collective+4core total; Q/G remains+4core/+3serial through one shorter return-tail stage. Fresh r2 physical evidence is required.

Other r1 placement-RC probes have native launch/capture within220/190ps: return199.43201/175.76641, serial167.18464/123.33573, fault join171.82346/143.29241. Return measured insertion mean284ps with263.5..327ps boundary spread63.5ps. No route has been submitted from these gates.

Each gate uses immutable CTS ODB, archived signoff SDC and actual TT cells with placement parasitics. Existing pinreg_audit parses the generated Liberty timing model against measured insertion means. Reusable tools/ref_tile/cts_native_probe.py fixes basename kit SDC paths and requires measured clock reference coverage, spread<=80ps and no combinational boundary pins as well as native launch/capture limits. The first return wrapper invocation failed on its SDC path before timing extraction; corrected invocation completed successfully. Early manual summaries predate the wrapper extra spread fields; retain their raw insertion and library records.

Personally viewed all four actual kit gate_layout floorplan.png and density.png pairs. Request showed a left cluster with E-to-W crossing; return W/E pin walls and middle mux cluster. Serial/fault join are compact. These are CTS images, not detailed route evidence. Gate result JSONs retain exact source bindings and remote run paths.
