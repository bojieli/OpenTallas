# HEAD r16 host west and mesh, 2026-11-21 03:15 PST

Viewed actual placed layout and density from each exact retained attempt.

- Host west attempt 2, `epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r16/items/hd_host_w/attempt_2/gen/hd_host_w/run/layout_review/place/{layout,density}.png`. Three bank rows keep through aisles open. The west edge and middle/lower bank rows carry most cell density while the north is largely open. Its existing output beat bank drives 512 bits to the west boundary without a local station, with 458 over 405 µm and a 742 µm maximum. Move the output bank toward that boundary or fit a protocol-matched station before an additional route. ISSUES.
- Mesh attempt 2, `epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r16/items/hd_mesh/attempt_2/gen/hd_mesh/run/layout_review/place/{layout,density}.png`. Six repeated bank rows leave visible east-west channels. The north shelf is a separate I/O bundle. The relevant west output bank has a load choke at the lower west edge and several isolated east sites. The lane-B output beat cohort reports 456/512 bits over 405 µm with a 675 µm maximum. The 18-bit adjacent wordline cohort also reaches 627 µm. Both cohorts need geometry work before an additional route. ISSUES.

The already admitted AP work may complete and provide timing/congestion measurements for those fixes.

## Existing beat registers, 2026-11-21 03:22 PST

Viewed mesh proposal epyc10:/srv/opentallas-scratch2/claude/head-crossing-1119/mesh_beat_codex1121/proposed_beat_sites.png. A fixed-anchor model placed 606 existing flops in the macro aisles with a 6.48 µm halo and did not move output registers or change cycles. Mesh lane B west-bound maximum drops from 675.4 to 397.06 µm, 456 to 0 over 405 µm. Lane A north-bound drops from 492.8 to 403.60 µm, 150 to 0 over 405 µm. Nearby macro and pin accesses still need a placed scan before timing or routing work. PASS for isolated DPL and geometry only.

The host west equivalent leaves 320 output wires over 405 µm and reaches 464.43 µm. The current D-side terminals keep too much of the cohort east of the macro banks. No further placement from that proposal. Work on the upstream payload cone or a matched beat handoff.

## Isolated placement result, 2026-11-21 03:25 PST

Viewed exact E10 `/srv/opentallas-scratch2/claude/head-crossing-1119/mesh_beat_codex1121/placed_beat_review.png`. Exact mesh a2 ODB derivative unit oth-ubuntu-2327394-1795260224, DPL zero illegal cells and sites, 606 selected changes. Ordered connectivity, pin coordinates and macro boundaries match the source. Placed data hop maxima B 675.405→397.062 µm and A 492.804→403.596 µm, with zero selected class hops over 405 µm. B clock driver span improves 527.969→374.906 µm. A clock driver span grows 558.571→665.383 µm. The plot shows the A move enters the open northeast area away from its current clock driver. Carry B alone into the next diagnostic and re-evaluate local clock assignment. Hold A for redesign. No route requested.
