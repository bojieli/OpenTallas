# S81 J9 D0 fW0 reset planned relay review

2026-11-23 15:28 PST. Exact preimage 170c034513f3 and relocation row 4944f93c23e9. After the B2 die-reset rebuild found a 7,728.5 µm hop from svc_9_att reset output 5 to fW0_p1_b0, the evenly spaced fallback put 13 of 28 relay centers in hard boxes. The original fallback remains held.

I viewed E10 `s81-j9-r6/compose/b2_1429/fw0_reset_sites_1527/layout.png`. The alternate relocates all 28 relay centers onto the die's 4.32 µm lattice, with 0.108 µm modeled hard-box margin and at most 70.784 µm transverse detour. Maximum modeled segment is 289.44 µm versus the 300 µm limit and the current die maximum of 290.1 µm. The source, destination and 28 registered stages are preserved. The stricter 275 µm planning sweep needed one extra stage. That variant remains separate.

PASS-COND for planned site and reach review. E10 unit 755947 is recomputing exact native wavefront endpoints and release after the move. Actual relay legal placement, parent clock/PG integration, overflight tracks and reviewed route evidence remain required.
