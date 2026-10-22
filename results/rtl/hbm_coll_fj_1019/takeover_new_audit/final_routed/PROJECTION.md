# Immutable FJ CLOSED-view projection

Fresh main base 4a7636d6723a50de327c7f50a0e9b4c3228c080c. Exact immutable records fj3=40d164681fcf12a64fb5e7227263bc764f7e5e18, fj2=265378acd12f8f75a94fce9565a72c04af1093cc; final audit d9dae199a. All 94 projected source blobs verified byte-identical in projection_blob_identity.json. No RTL/global helper/engine/parent pointer changes.

Complete percorner TT/FF/SS IO audit compares all454/461 actual final BTerms to every Liberty pin: every nonclock input has setup/hold, every dynamic output has rising-edge arcs; five untimed output bits each have explicit actualfinal TIELO drivers (fault_cause[15,14,8],issuer_cfg[35,34]), documented in output_constant_classes.json. Exported immutable Liberty does not encode a function for those constant output pins; no dynamic path is omitted. Power pins are present as expected.

One rawnativeSRAM clock per tile u_ot_pr_core.u.u_program.u_flow/clk, 1/1 coverage, clockfamily core_clk includes all3038/3046 sinks. Native SRAM references use rawpin arrival (zero child-flop offset), exact macro included. No forwarded clock output on these tiles. Actual TT/FF allsink spread26.2/26.2 and29.2/28.9ps; exported full rising/falling min/max tree envelopes41.16663/34.52226 and44.45693/37.68263ps, each<=80. Complete perpin and clock receipts export_complete_clock_io_audit.json. Both final nativePG/native32/fulltransparentreach/TTsetupFFholdDRC audits PASS as FINAL_PACKET.md.

Only root may merge this projection. Parent pointer/source-age bind still requires own literal geometry and actual source-to-capture reach; no automatic promotion.
