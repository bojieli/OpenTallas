# Native forwarding capability evidence

Exact exporter source: 35e931766b755a6432d5663dff461a25a57d3a43, tools/tt_views/view_export.py SHA256 578418117d3547dc46dcf08c119533d1fc36db122a7a8c22f44cf6d4ae7b82b3. SOURCE35/view_export.py is the exact committed file, independently checked against git show. No parallel working-tree exporter was used. Initial28ad runs are retained.

Native OpenROAD routed/OpenRCX coupons: unary BUF, unary INV, BUF→INV→BUF with a separate DFF data path, source latency17ps, waveform23/377ps, period900ps, output clock load37fF. Native rebuilt default clk_in/clk_out BUF/INV are also included. This is exporter capability evidence; these tiny coupons are not closure-qualified parent views.

NATIVE_PROOF.json records15 allcorner exports, all nonforwarded pin/FF/outside-output bytes identical to sequential raw native ETM, exact original OT_WS before forwarded mutations, three latency17→0 invariant local-delay/table comparisons (all absolute arrivals shift17ps), absent-default explicit-name no receipt, six expected causal rejections, and changed arrival/table with output load74fF or full SPEF R/C doubled. Input ODB/SPEF/V/SDC, native extraction Tcl/logs/raw main ETM/clock-free raw ETM/final Liberty, recipe and failures are included. FILES_SHA256.json pins collected bytes. native_proof.py reruns the artifact comparisons.

Original archived EW halfcycle routed ODB/SPEF remains absent; this capability proof does not authorize reconstructing or replacing its historical view. Root must review the shared source patch before publication or actual reexport. No die GRT is authorized by this packet.
