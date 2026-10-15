Service-band source-exact geometric successor

Prerequisite: install the scalar per-PC-clock wrappers from 41faf638c /
00fcd6406 (recovered by HBM hardener). Slot source_sha256 pins every wrapper.
No source/port/parameter or CLOSED PC view is renamed or fabricated here.

Five n1..n5 Tcl files implement one exact physical pin plan per count.
The seventeen compressed JSON files retain every actual wrapper connection,
its unchanged CLOSED PC LEF endpoint, the parent pin and Manhattan distance.
Same-count Tcl byte equality is asserted before any shared plan is emitted.
The 34 die instances retain the adopted band homes and mirror orientations.

The row is compact and centered, with 32.4 um gaps and 172.8 um pitch. Every child origin is on
the 43.2 um common lattice. Its y=259.2 leaves 28.08 um to the north edge. North/south data pins are grouped per PC; the
individual clk_pc entries sit above their own child clock pin. All physical
bits, including each reset fanout endpoint, fit the 500 um rule.
Worst n1/n2/n3=317.466 um, n4=384.918 um, n5=454.482 um.
Service clocks are the actual 1024 ps HBM domain. Per-PC compensation remains
open; no generic child insertion or spread is promoted as a native clock view.
No added data edge or FF; the existing PC logic and LEF remain unchanged.

PG M7 / die straps M8 / parent signals through M6 provide the actual hierarchy
over M5-capped children. This is a typed cluster grant, not a layer waiver.
Kit sources must use the supplied io_tcl and exact child origins; the old
placer-generated aggregate-bus offsets are superseded only for these bands.

These are geometry and source-binding receipts. Existing PC launch 408.99 ps,
capture 508.02 ps and spread 104.7 ps still fail the native boundary budget.
The original n1 route ended TT -220.50 ps / FF +63.16 ps / DRC0.
Fresh source-bound CTS/gate/TT-setup/FF-hold/DRC proof is required; SS is only
a sensitivity. External die links, compensated clock delivery and complete
source-contract joins remain open. No die GRT/STA closure is claimed.

Reproduce after source prerequisite publication:
python3 tools/hbm_die_v15/service_pins.py --pc-lef \
 physical/ref_tile/hv15_svc_pc/views/ot_hbm_svc_static_pc/ot_hbm_svc_static_pc.lef

Run after grants.py: its previous generic pin packer cannot preserve these
per-PC windows. The source and leaf LEF hashes must match the receipts.
