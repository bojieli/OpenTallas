# Selector landed parent with CLOSED children

Four exact s3u_b quadrant views (CLOSED hidx_sel_s3u_b-s3ub-d903bcf15, record5bd53e4cb) and one s3d_a control view from main replace obsolete s3q/s3c view names. Dedicated hard-build RTL strips child DMUT=0 parameter overrides because exported hard cells have no parameters; original generated RTL and lockstep bench remain unchanged.

SAFE pre-gate review10-21 09:53:
1 inherited hard-child face registers / fixed landing control rings.
2 planned direct line buses and inherited ring hops; W-to-right-column x388.8um, clock/reset routes use continuous channels. Measured reach/timing remain gate obligations.
3 native census must pass before layout; no waiver.
4 no new arithmetic or cycles; child s3u_b and ctl s3d_a retain measured stages.
5 child SRAM and source identities unchanged.
6 fixed old600x450 floorplan:691.2x648, child origins43.2lattice; four259.2x216 quadrants at x43.2/388.8,y43.2/388.8,29.16sq ctl at302.4,302.4; continuous86.4vertical /129.6horizontal cell bands and43.2outer channels. Fill measured from synth.
7 five local region clocks and fixed-latency control landing rings inherited; no cross-region direct register paths introduced.
8 existing regional reset forest, no new reset network.

Die slot grows600x450 to691.2x648, no logical latency delta. Existing LP lockstep and mutant witnesses are retained. Preflight geometry/pins/RTL PASS; native/CTS/GRT still required.
