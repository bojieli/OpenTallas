# HBM-SMB-KITS pre-route review packet

This candidate is for a coordinator visual review. No REVIEW.json and no route submission are authorized in this lane. No closure or production qualification is claimed.

Safe-design checklist, reviewed against relative RTL before CTS gate:

1. PASS by source inspection: data inputs land in existing RTL pin flops and outputs are register Qs. Pin register insertion is disabled to preserve the compiler-fixed launch edges. Reset uses two plain landing flops (cp target RSYNC=1; XC kit reset_landing stages=2).
2. PASS geometry: outline diagonal below 500 um and maximum Manhattan distance in one axis below 405 um. All boundary pins use a full face; remote mapped wire-reach lint remains authoritative before adoption.
3. PENDING mapped measurement: no intended critical control has shared combinational arbitration; gate fanout lint must confirm <=~32 load guidance and reject structural violations. No false-path or multicycle exceptions.
4. PENDING mapped measurement: issuer-relative arithmetic is pipelined, XC R/C stages are registers, collar writes and launches are registered. Gate depth and timing must confirm the physical budget.
5. PASS storage: cp is a register-only collar without a runtime-indexed large store. XC contains exactly two 1024x256 SRAM programme macros plus two 128x256 SRAM descriptor macros; no flop replacement.
6. PASS planned geometry: square outlines, XC macro origins on 43.2 um lattice, wide horizontal standard-cell band between programme macros, full-face W pins on XC. SRAM macro face density under 6 pins/um. Synthesis area and actual placed utilization are pending; do not adopt if utilization is outside the safe range without structural resizing.
7. PASS configured policy: local CTS; hold margins 0.030 ns. Gate must measure TT and FF pin-flop spread <=80 ps; neighbour-matched reference and native timing remain adoption requirements. Insertion alone is not a rejection.
8. PASS static protocol: no credits added and no data-path stage added versus committed relative masters. cp cfg->write and launch->run remain 2 edges; XC keeps the relative R/C alignment. Reset landing adds reset settling only, before static install. Added physical pin registers would need compiler/die repricing.

Measurements required in coordinator packet: gate_layout PNG, mapped area/utilization, macro lattice and channels, full-face pin density, clock root relative to register mass, TT/FF insertion/spread, timing, and lint. Any failed gate/route requires classifying its cause; a failed route requires structural redesign.

Pin-bound utilization exception, HBM coordinator 10-19: the measured 446 um2 cells cannot occupy 40-60% while 895 registered pins fit at <=6 pins/um. Three 256-bit buses occupy separate complete N/S/E faces; controls/clock W. 51.84 um square gives 4.94 pins/um per bus before end clearance, <=5.4 with 2.16 um clearance. Cell utilization is ~20%; this is a measured interface-area constraint, not a large speculative logic margin. No SRAM macros. The entire outline is one connected cell region. Boundary timing, reach and clock spread still must pass the new gate.

Direct behavioural qualification (fleet ot-epyc5, source3b68a5ed4): exact PASS; arg-off-by-one mutant1 FAIL; target-ignore mutant2 FAIL. Logs committed under results/rtl/hbm_ds_layer_tput_1018/smb_kits_1019/.
