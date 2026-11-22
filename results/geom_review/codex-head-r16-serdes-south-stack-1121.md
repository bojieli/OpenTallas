# HEAD r16 SerDes south access draft · 2026-11-21 16:38 PST

Viewed the actual failed-GRT marker and clock-site geometry overlaid with the draft split in `epyc9:/srv/opentallas-scratch3/claude/head-crossing-1119/serdes_s_access_1619/candidate/serdes_south_draft.png`. The old r16 job `33deec685c72` ended structurally with 671 detailed overflow units, all near the south edge and dominated by PMA RX and collective ingress/egress. Exact stalled GRT DB read found 84nm PMA and 192nm collective boundary rectangles, unchanged by the draft.

Two blanket M1–M7 sites account for the two edge concentrations at x1671.354–1703.970 and x1802.412–1835.514 µm. Frozen tree `564220a7b28e` supplies four and two actual clock-stack windows, respectively. Draft `146f383f57ec` keeps the full M1–M2 and placement reservation and restores 23.976 and 28.782 µm of M3–M7 span. All 24 collective boundary ports, 12,336 tracks and the native PMA pin plan stay identical. One sampled collective BTerm (`coll_o0[178]`) remains aligned with an actual stack window and needs a jog in the future GRT proof.

Review covers the source draft. Check the exact generated and placed geometry before CTS/GRT. Detail route remains held.
