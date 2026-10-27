# Thin current-main merged clock adapter

Current main has no consumer for C15's explicit merged_clock_ports tap lists. This packet applies only afdd0a5e6 and bad28a751 onto current main; there is no physical-plan or native-reset ancestry. The optional tap list expands into two exact scalar rows on one actual clock tap. Selected native LEF/Lib clock identities and per-bit pin coordinates must agree. The runtime binder connects both actual ITerms and rejects missing, nonclock, or wrong-source endpoints. Each bit's latency table maps to the same tap; no scalar clk_pair port is fabricated.

The helper, executable positive/mutant tests, Tcl binder, core_tap_rows and core_tap_of mechanisms are unchanged from the qualified candidate. Existing receipts remain5focused plus14CP2/clat (1skip), with8followup focused/corelat; both-bit positive and missing-bit/Lib/geometry controls are included. No test wave or physical job was repeated. The machine schema is regenerated from current Python schema, preserving current fields and adding only the optional list.

Actual selected native views are mandatory at physical kit generation. Plan-only sidecar metadata cannot fabricate a LEF clock pin or connect a net. Default scalar behavior stays unchanged.
