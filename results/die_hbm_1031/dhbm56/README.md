# DIE-HBM-56 (2026-10-31) HBM g50 freeze line: one-block ft station siting (q_b011, q_b110__physical_v1)
Root cause (attr.py on GRT congestion reports): station clumps. Slots without bit_sites put all bits of a station on ONE
point (b110pv1 L6br0_2 828 b: st0 (142.6,1162.1) in the lane0/lane1 channel, st1 (406.1,1062.7); q_b011 L183mx2 569 b at
(8.64,3792.96)); q_b011 L15x1 4128 b vertical demand in the 103-um E strip.
site_box.py (= DIE-HBM-55 site_strip.py generalised): per-bit sites for internal stations, station counts unchanged,
station0 beside its in pin (g2/face_flops convention), per-bit hop <= 394.9 asserted, other slots' sites reserved.
Plans on d44q_B (DIE-HBM-55: d44p + L15x1 E-strip B), intel1 /srv/opentallas-scratch2/claude/die-hbm-56/plan:
- r1: L42x4 E strip at out y + L183mx2 W strip + L6br0_2 channel x180-280 -> G0C +1 ERROR (L183m hop 370 > 364): dropped.
- r2: L42x4 gap box x150-230 y1031-1129 + L183mx2 E strip x245-300 + L6br0_2 channel rank-linear x100-300: G0/G0C 0 new/0 gone.
- r3_0.08 = r2 + L15x1 last hop keeps 8% of dy (diagonal M6/M7 over the macro column): G0/G0C 0 new/0 gone (q 0.1: +1 G0C, dropped).
G2 0-it (current g2, main f1a8dcffa6e): q_b011 d44p 1,026,793 / B 605,087 / r1 527,892 / r2 526,616 / r3_0.08 353,666 / r3_0.1 316,190;
q_b110pv1 d44q_B 35,091 / r1 9,374 / r2 9,037. 50-it runs: intel1 die-hbm-56/g2/*_i50, epyc2 die-hbm-55/g2/d44q_B_i50.
