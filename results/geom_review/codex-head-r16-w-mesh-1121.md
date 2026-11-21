# HEAD r16 host west and mesh, 2026-11-21 03:15 PST

Viewed actual placed layout and density from each exact retained attempt.

- Host west attempt 2, `epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r16/items/hd_host_w/attempt_2/gen/hd_host_w/run/layout_review/place/{layout,density}.png`. Three bank rows keep through aisles open. The west edge and middle/lower bank rows carry most cell density while the north is largely open. Its existing output beat bank drives 512 bits to the west boundary without a local station, with 458 over 405 µm and a 742 µm maximum. Move the output bank toward that boundary or fit a protocol-matched station before an additional route. ISSUES.
- Mesh attempt 2, `epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r16/items/hd_mesh/attempt_2/gen/hd_mesh/run/layout_review/place/{layout,density}.png`. Six repeated bank rows leave visible east-west channels. The north shelf is a separate I/O bundle. The relevant west output bank has a load choke at the lower west edge and several isolated east sites. The lane-B output beat cohort reports 456/512 bits over 405 µm with a 675 µm maximum. The 18-bit adjacent wordline cohort also reaches 627 µm. Both cohorts need geometry work before an additional route. ISSUES.

The already admitted AP work may complete and provide timing/congestion measurements for those fixes.
