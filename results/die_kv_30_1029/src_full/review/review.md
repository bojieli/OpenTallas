# DIE-KV-30-SRC fresh full-union source review, 2026-10-29 09:32 PDT
Pictures (viewed by Claude DIE-KV-30-SRC): receipts/render_new_native.png (die + 600x1300um), receipts/renderz_new_native.png (40x30um zoom) vs receipts/render*_old_native.png.
PASS-COND for provider import into the rebuilt source: die-level clock body distribution and partition/hard-core layout are identical to the old source (block/clock placement sha equal); at the zoom the packed clock bodies now sit inside a white M1 OBS window, where the old source had solid M1 OBS over them.
Readback CHECKED: 15456 insts (160 blocks + 15296 clock), clock bodies hitting any master OBS 0 (old 14634), hard-core hits 0, 56/56 masters signal-pin sha equal, sizes equal. Preflight of the SAME proposal_open placements against the new fresh constraints: READY_FOR_REVIEW, 0 issues.
No timing, PG, IR, routed or freeze claim.
