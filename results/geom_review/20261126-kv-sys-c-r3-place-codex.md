# KV SYS_C R3 exact global placement

**Fix first. Route held.** Viewed exact E10 R3 3_3_place_gp density, RUDY, path and macro/PG overlays. The central UCIe macro spans x691.308–1468.908 and y60.480–838.080. Four SRAM banks sit just north of it. Their lower line at y865.980 leaves 27.90 µm to the UCIe body. The two internal SRAM pair gaps are 12.088 µm each. North-edge traffic converges there and around the east turn. Estimated demand p99.5/max is 64.455/87.921. There is usable area east and west of the central macro. The overlay shows 951 PG stripes and no drawn macro-pin overlaps. Electrical continuity and actual halos are still unqualified by this render.

Exact ideal 833 ps placement timing reports 309 endpoints below −150 ps and WNS −15148.993 ps. The worst path is compiled KVN identity bit 18 to the KVN word-identity register, through _63323_/Y. Its two large increments are 4154.937 and 11441.126 ps. Compare the buffered detailed-placement result before changing the RTL or stage count.

E10 path /srv/opentallas-scratch2/claude/noprog-review/vis_review/kv-sysc-r3-place-e10-1126. This is the exact noncounting ffafefc46dce place-only diagnostic. No CTS or route result. The separate OBS1 candidate remains parked pending the detailed-placement findings.
