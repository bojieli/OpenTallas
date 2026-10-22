# EMB C7 structural replacement

Replace measured c6 boundary clock spread failures with centered ck entry, physically bounded clock leaves and complete equal-depth stage accounting. MY SRAM orientation faces read pins toward East payload captures. Exact payload RTL and data-edge prices unchanged.

Safety checklist: same single ck domain; all actual FF and SRAM clock entries retained; no timing exception; no extra payload edge. Every clock path receives the complete maximum stage budget, including binary node and final leaf drivers. Leaf construction continues until Manhattan bounding-box span is at most 40 um. Existing 35 ps measured leaf equalization is retained. Centered S ck prevents the prior far-West stem. SRAM MY orientation keeps macro read pins toward East captures. Source manifest and native obligations are inherited unchanged. Actual gate results and ROOT PNG review remain required before normal submission.
